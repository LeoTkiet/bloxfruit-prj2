"""Griductive Game Engine (owned by TV1).

Enforces the strict architectural boundary between:
- Hidden World (private inside GameEngine: complete puzzle, hidden statuses, unrevealed clues)
- Public World (immutable `PublicState` snapshots passed to `ILogicAgent` and `GUI`)

Implements `IGameEngine` from `core.contracts.interfaces`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from core.contracts.interfaces import ICNFEncoder, ILogicAgent
from core.contracts.models import (
    CellID,
    CharacterPublicInfo,
    Clue,
    PublicState,
    RegionSpec,
    Status,
    VerdictCode,
    VerdictResponse,
)
from engine.puzzle_loader import (
    HiddenCharacter,
    PuzzleDefinition,
    load_puzzle_definition,
)
from engine.puzzle_validator import (
    extract_clue_referenced_cells,
    validate_puzzle,
)


class GameEngine:
    """Authoritative game state owner for Griductive.

    Uses Dependency Injection for `ILogicAgent` (verdict entailment check) and
    optionally `ICNFEncoder` / `region_resolver` (clue cell highlighting).
    """

    def __init__(
        self,
        logic_agent: Optional[ILogicAgent] = None,
        encoder: Optional[ICNFEncoder] = None,
        region_resolver: Optional[Callable[[RegionSpec, int], list[CellID]]] = None,
    ) -> None:
        self._agent: Optional[ILogicAgent] = logic_agent
        self._region_resolver: Optional[Callable[[RegionSpec, int], list[CellID]]] = (
            region_resolver
            if region_resolver is not None
            else (encoder.resolve_region if encoder is not None else None)
        )

        # Private hidden world — NEVER exposed directly to callers
        self._puzzle: Optional[PuzzleDefinition] = None
        self._characters_by_cell: dict[CellID, HiddenCharacter] = {}
        self._revealed_set: set[CellID] = set()
        self._proved_verdicts: dict[CellID, Status] = {}
        self._step: int = 0

    def set_logic_agent(self, logic_agent: ILogicAgent) -> None:
        """Attach or replace the injected ILogicAgent (useful for DI wiring)."""
        self._agent = logic_agent

    def set_region_resolver(
        self,
        region_resolver: Callable[[RegionSpec, int], list[CellID]],
    ) -> None:
        """Attach or replace the region resolver used for clue highlighting."""
        self._region_resolver = region_resolver

    def _require_loaded(self) -> PuzzleDefinition:
        if self._puzzle is None:
            raise RuntimeError("No puzzle is currently loaded. Call load_puzzle() first.")
        return self._puzzle

    def _initialize_from_definition(self, puzzle: PuzzleDefinition) -> PublicState:
        self._puzzle = puzzle
        self._characters_by_cell = {ch.cell_id: ch for ch in puzzle.characters}
        self._revealed_set = set(puzzle.initial_revealed)
        self._proved_verdicts = {
            cid: self._characters_by_cell[cid].hidden_status
            for cid in puzzle.initial_revealed
        }
        self._step = 0
        return self.get_public_state()

    # ------------------------------------------------------------------
    # IGameEngine implementation
    # ------------------------------------------------------------------

    def load_puzzle(self, path: str | Path) -> PublicState:
        """Load, validate, and initialize a puzzle from a JSON file."""
        puzzle = load_puzzle_definition(path)
        validate_puzzle(puzzle)
        return self._initialize_from_definition(puzzle)

    def load_puzzle_definition(self, puzzle: PuzzleDefinition) -> PublicState:
        """Validate and initialize directly from an in-memory PuzzleDefinition."""
        validate_puzzle(puzzle)
        return self._initialize_from_definition(puzzle)

    def restart(self) -> PublicState:
        """Reset the currently loaded puzzle back to its initial public state (t = 0)."""
        puzzle = self._require_loaded()
        return self._initialize_from_definition(puzzle)

    def get_public_state(self) -> PublicState:
        """Build and return a fresh, deeply immutable PublicState snapshot.

        Guarantees:
        - Face-down cards have `is_revealed=False`, `status=Status.UNKNOWN`, `clue=None`.
        - `revealed_clues` contains ONLY clues of currently face-up cards.
        - `proved_verdicts` is wrapped in `MappingProxyType` by `PublicState`.
        """
        puzzle = self._require_loaded()

        public_chars: list[CharacterPublicInfo] = []
        revealed_clues: list[Clue] = []

        for ch in puzzle.characters:
            if ch.cell_id in self._revealed_set:
                proved_status = self._proved_verdicts[ch.cell_id]
                public_chars.append(
                    CharacterPublicInfo(
                        cell_id=ch.cell_id,
                        name=ch.name,
                        profession=ch.profession,
                        status=proved_status,
                        is_revealed=True,
                        clue=ch.hidden_clue,
                    )
                )
                revealed_clues.append(ch.hidden_clue)
            else:
                public_chars.append(
                    CharacterPublicInfo(
                        cell_id=ch.cell_id,
                        name=ch.name,
                        profession=ch.profession,
                        status=Status.UNKNOWN,
                        is_revealed=False,
                        clue=None,
                    )
                )

        is_solved = len(self._revealed_set) == len(puzzle.characters)

        return PublicState(
            puzzle_id=puzzle.puzzle_id,
            puzzle_name=puzzle.name,
            grid_size=puzzle.grid_size,
            step=self._step,
            characters=tuple(public_chars),
            proved_verdicts=dict(self._proved_verdicts),
            revealed_clues=tuple(revealed_clues),
            is_solved=is_solved,
        )

    def submit_verdict(self, cell: CellID, status: Status) -> VerdictResponse:
        """Evaluate a player/agent verdict using ONLY public knowledge via ILogicAgent.

        Rules (Spec Sections 2.2, 3.4, 4.1):
        - Rejects invalid cell IDs or non-concrete verdicts (UNKNOWN).
        - If KB_t is unsatisfiable -> returns INCONSISTENT without mutating state.
        - If neither status is forced -> returns NOT_PROVABLE without mutating state or
          revealing any hidden clue.
        - If the opposite status is forced -> returns CONTRADICTED without mutating state
          or revealing any hidden clue.
        - If `status` is logically entailed -> accepts the verdict, reveals the card and
          its clue, advances step t -> t + 1, and returns ACCEPTED with updated PublicState.
        """
        self._require_loaded()
        if self._agent is None:
            raise RuntimeError(
                "GameEngine has no ILogicAgent attached. Inject one via __init__ or set_logic_agent()."
            )

        cell_upper = cell.upper()
        if cell_upper not in self._characters_by_cell:
            raise ValueError(f"Unknown cell_id {cell!r} for current puzzle")

        if status not in (Status.CRIMINAL, Status.INNOCENT):
            raise ValueError(
                f"Submitted verdict must be CRIMINAL or INNOCENT, got {status!r}"
            )

        current_public = self.get_public_state()

        # Already revealed card: do not mutate state or advance step
        if cell_upper in self._revealed_set:
            proved = self._proved_verdicts[cell_upper]
            if proved == status:
                return VerdictResponse(
                    code=VerdictCode.ACCEPTED,
                    cell=cell_upper,
                    submitted_status=status,
                    public_state=current_public,
                    revealed_clue=self._characters_by_cell[cell_upper].hidden_clue,
                    message=f"{cell_upper} is already proved as {proved.value}.",
                )
            return VerdictResponse(
                code=VerdictCode.CONTRADICTED,
                cell=cell_upper,
                submitted_status=status,
                public_state=current_public,
                revealed_clue=None,
                message=(
                    f"{cell_upper} is already proved as {proved.value}, "
                    f"which contradicts {status.value}."
                ),
            )

        # 1. Check KB_t consistency using ONLY PublicState
        if not self._agent.check_consistency(current_public):
            return VerdictResponse(
                code=VerdictCode.INCONSISTENT,
                cell=cell_upper,
                submitted_status=status,
                public_state=current_public,
                revealed_clue=None,
                message="Current public knowledge base KB_t is inconsistent (UNSAT).",
            )

        # 2. Classify cell strictly from PublicState via logical entailment
        entailed = self._agent.classify_character(current_public, cell_upper)

        if entailed == Status.UNKNOWN:
            return VerdictResponse(
                code=VerdictCode.NOT_PROVABLE,
                cell=cell_upper,
                submitted_status=status,
                public_state=current_public,
                revealed_clue=None,
                message=(
                    f"Verdict {status.value} for {cell_upper} is not yet provable "
                    f"from the currently revealed clues (no guessing allowed)."
                ),
            )

        if entailed != status:
            return VerdictResponse(
                code=VerdictCode.CONTRADICTED,
                cell=cell_upper,
                submitted_status=status,
                public_state=current_public,
                revealed_clue=None,
                message=(
                    f"Verdict {status.value} for {cell_upper} is contradicted: "
                    f"the current knowledge base forces {entailed.value}."
                ),
            )

        # 3. Sanity guard: verify entailed verdict matches the hidden ground truth
        hidden_char = self._characters_by_cell[cell_upper]
        if hidden_char.hidden_status != status:
            return VerdictResponse(
                code=VerdictCode.INCONSISTENT,
                cell=cell_upper,
                submitted_status=status,
                public_state=current_public,
                revealed_clue=None,
                message=(
                    f"Puzzle inconsistency detected: KB_t entails {status.value} for "
                    f"{cell_upper}, which conflicts with the puzzle's hidden solution."
                ),
            )

        # 4. Accept verdict, flip card, reveal clue, advance step t -> t + 1
        self._revealed_set.add(cell_upper)
        self._proved_verdicts[cell_upper] = status
        self._step += 1

        updated_public = self.get_public_state()
        return VerdictResponse(
            code=VerdictCode.ACCEPTED,
            cell=cell_upper,
            submitted_status=status,
            public_state=updated_public,
            revealed_clue=hidden_char.hidden_clue,
            message=f"Accepted: {cell_upper} ({hidden_char.name}) is {status.value}.",
        )

    def get_highlighted_cells(self, cell: CellID) -> list[CellID]:
        """Return cells referenced or counted by `cell`'s clue IF `cell` is revealed.

        If `cell` is currently face-down, returns [] so hidden clue targets are never leaked.
        """
        puzzle = self._require_loaded()
        cell_upper = cell.upper()
        if cell_upper not in self._characters_by_cell:
            raise ValueError(f"Unknown cell_id {cell!r} for current puzzle")

        if cell_upper not in self._revealed_set:
            return []

        clue = self._characters_by_cell[cell_upper].hidden_clue
        return extract_clue_referenced_cells(
            clue=clue,
            grid_size=puzzle.grid_size,
            region_resolver=self._region_resolver,
        )

    def get_all_clues_for_uniqueness(self) -> list[Clue]:
        """Return the complete clue list for offline uniqueness verification."""
        puzzle = self._require_loaded()
        return [ch.hidden_clue for ch in puzzle.characters]
