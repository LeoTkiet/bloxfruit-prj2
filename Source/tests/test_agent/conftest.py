"""Shared helpers, spies, and builders for `tests/test_agent/`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from core.contracts.interfaces import IGameEngine, ISATSolver
from core.contracts.models import (
    CellID,
    CharacterPublicInfo,
    Clue,
    CNFFormula,
    PublicState,
    SATResult,
    Status,
    VerdictCode,
    VerdictResponse,
    all_cell_ids,
)
from engine.puzzle_loader import HiddenCharacter, PuzzleDefinition

PUZZLES_DIR = Path(__file__).resolve().parents[2] / "puzzles"


def make_public_state(
    grid_size: int,
    *,
    puzzle_id: str = "test_puzzle",
    puzzle_name: str = "Test Puzzle",
    step: int = 0,
    proved_verdicts: Optional[Mapping[CellID, Status]] = None,
    revealed_clues: Sequence[Clue] = (),
) -> PublicState:
    """Build a valid immutable `PublicState` for unit tests."""
    proved = dict(proved_verdicts or {})
    clue_by_owner = {c.owner: c for c in revealed_clues}

    characters: list[CharacterPublicInfo] = []
    for cid in all_cell_ids(grid_size):
        if cid in proved:
            characters.append(
                CharacterPublicInfo(
                    cell_id=cid,
                    name=f"Char_{cid}",
                    profession="Tester",
                    status=proved[cid],
                    is_revealed=True,
                    clue=clue_by_owner.get(cid),
                )
            )
        else:
            characters.append(
                CharacterPublicInfo(
                    cell_id=cid,
                    name=f"Char_{cid}",
                    profession="Tester",
                    status=Status.UNKNOWN,
                    is_revealed=False,
                    clue=None,
                )
            )

    is_solved = len(proved) == grid_size * grid_size
    return PublicState(
        puzzle_id=puzzle_id,
        puzzle_name=puzzle_name,
        grid_size=grid_size,
        step=step,
        characters=tuple(characters),
        proved_verdicts=proved,
        revealed_clues=tuple(revealed_clues),
        is_solved=is_solved,
    )


def make_puzzle_definition(
    puzzle_id: str,
    grid_size: int,
    hidden_statuses: Mapping[CellID, Status],
    clues: Mapping[CellID, Clue],
    initial_revealed: Sequence[CellID],
    *,
    expected_status: str = "SOLVABLE",
) -> PuzzleDefinition:
    """Build an in-memory `PuzzleDefinition` with alphabetical character names."""
    cells = all_cell_ids(grid_size)
    characters = tuple(
        HiddenCharacter(
            cell_id=cid,
            name=f"Name_{idx:02d}",
            profession="Detective",
            hidden_status=hidden_statuses[cid],
            hidden_clue=clues[cid],
        )
        for idx, cid in enumerate(cells)
    )
    return PuzzleDefinition(
        puzzle_id=puzzle_id,
        name=f"Synthetic {puzzle_id}",
        grid_size=grid_size,
        characters=characters,
        initial_revealed=tuple(initial_revealed),
        expected_status=expected_status,
    )


class SpySATSolver:
    """Wrapping `ISATSolver` spy recording call count and call history."""

    def __init__(self, inner: ISATSolver) -> None:
        self._inner = inner
        self.call_count: int = 0
        self.call_history: list[tuple[tuple[int, ...], int, bool]] = []

    def reset_stats(self) -> None:
        self.call_count = 0
        self.call_history.clear()

    def solve(
        self,
        cnf: CNFFormula,
        assumptions: Sequence[int] = (),
    ) -> SATResult:
        res = self._inner.solve(cnf, assumptions=assumptions)
        self.call_count += 1
        self.call_history.append((tuple(assumptions), cnf.num_clauses, res.is_sat))
        return res


class IsolationTrapGameEngine:
    """IGameEngine wrapper/trap detecting any hidden-data or forbidden access."""

    def __init__(
        self,
        inner: IGameEngine,
        *,
        override_submit: Optional[
            Callable[[CellID, Status, IGameEngine], VerdictResponse]
        ] = None,
    ) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_override_submit", override_submit)
        object.__setattr__(self, "submitted_verdicts", [])
        object.__setattr__(self, "uniqueness_accessor_called", False)
        object.__setattr__(self, "forbidden_accesses", [])

    # Trap properties mimicking hidden GameEngine internals
    @property
    def hidden_solution(self) -> Any:
        self.forbidden_accesses.append("hidden_solution")
        raise AssertionError("Agent attempted to read hidden_solution!")

    @property
    def unrevealed_clues(self) -> Any:
        self.forbidden_accesses.append("unrevealed_clues")
        raise AssertionError("Agent attempted to read unrevealed_clues!")

    @property
    def _puzzle(self) -> Any:
        self.forbidden_accesses.append("_puzzle")
        raise AssertionError("Agent attempted to read _puzzle!")

    @property
    def _characters_by_cell(self) -> Any:
        self.forbidden_accesses.append("_characters_by_cell")
        raise AssertionError("Agent attempted to read _characters_by_cell!")

    def __getattr__(self, name: str) -> Any:
        self.forbidden_accesses.append(name)
        raise AssertionError(f"Agent accessed non-IGameEngine attribute {name!r}!")

    def load_puzzle(self, path: str | Path) -> PublicState:
        return self._inner.load_puzzle(path)

    def get_public_state(self) -> PublicState:
        return self._inner.get_public_state()

    def submit_verdict(self, cell: CellID, status: Status) -> VerdictResponse:
        self.submitted_verdicts.append((cell, status))
        if self._override_submit is not None:
            return self._override_submit(cell, status, self._inner)
        return self._inner.submit_verdict(cell, status)

    def restart(self) -> PublicState:
        return self._inner.restart()

    def get_highlighted_cells(self, cell: CellID) -> list[CellID]:
        return self._inner.get_highlighted_cells(cell)

    def get_all_clues_for_uniqueness(self) -> list[Clue]:
        object.__setattr__(self, "uniqueness_accessor_called", True)
        return self._inner.get_all_clues_for_uniqueness()
