"""Abstract interfaces (Ports) defining module boundaries for Griductive Solver.

Each team member implements their own Port and depends ONLY on other members'
Ports (via Dependency Injection), enabling fully parallel development and
mock-based unit testing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Protocol, Sequence, runtime_checkable

from core.contracts.models import (
    CellID,
    Clue,
    CNFFormula,
    CNFStats,
    DeductionStep,
    HintResult,
    PublicState,
    RegionSpec,
    SATResult,
    Status,
    UniquenessResult,
    VerdictResponse,
)


@runtime_checkable
class IGameEngine(Protocol):
    """Port owned by TV1 (`engine/`), consumed by TV4 (Auto Solve) and TV5 (GUI).

    Owns the complete puzzle, hidden solution, and unrevealed clues.
    Exposes ONLY immutable `PublicState` snapshots to callers.
    """

    def load_puzzle(self, path: str | Path) -> PublicState:
        """Load, validate, and initialize a puzzle from a JSON file."""
        ...

    def get_public_state(self) -> PublicState:
        """Return an immutable snapshot of revealed clues and proved verdicts."""
        ...

    def submit_verdict(self, cell: CellID, status: Status) -> VerdictResponse:
        """Validate a verdict via ILogicAgent; reveal card iff logically entailed."""
        ...

    def restart(self) -> PublicState:
        """Reset the currently loaded puzzle back to its initial public state (t = 0)."""
        ...

    def get_highlighted_cells(self, cell: CellID) -> list[CellID]:
        """Return all cells referenced or counted by a *revealed* card's clue.

        Returns an empty list if `cell` is currently face-down (never leaks hidden clues).
        """
        ...

    def get_all_clues_for_uniqueness(self) -> list[Clue]:
        """Return the complete clue set exclusively for offline puzzle uniqueness checks."""
        ...


@runtime_checkable
class ICNFEncoder(Protocol):
    """Port owned by TV2 (`logic/`), consumed by TV4 (Agent) and TV1 (Highlight)."""

    def map_cell_to_var(self, cell: CellID, grid_size: int) -> int:
        """Deterministically map a CellID to its primary variable index (1..N^2)."""
        ...

    def resolve_region(self, region: RegionSpec, grid_size: int) -> list[CellID]:
        """Resolve a RegionSpec into a deterministic list of distinct CellIDs."""
        ...

    def encode_kb(self, public_state: PublicState) -> tuple[CNFFormula, CNFStats]:
        """Encode KB_t = CNF(revealed clues) & UnitClauses(proved verdicts)."""
        ...

    def encode_clue(self, clue: Clue, grid_size: int) -> list[list[int]]:
        """Encode a single structured Clue into CNF clauses."""
        ...


@runtime_checkable
class IDirectEvaluator(Protocol):
    """Port owned by TV2 (`logic/`), used as ground-truth oracle for CNF verification."""

    def evaluate_clue_direct(
        self,
        clue: Clue,
        assignment: Mapping[CellID, bool],
        grid_size: int,
    ) -> bool:
        """Directly evaluate whether `clue` holds under a complete boolean assignment
        (True = Criminal, False = Innocent) without invoking the CNF encoder.
        """
        ...


@runtime_checkable
class ISATSolver(Protocol):
    """Port owned by TV3 (`solver/`), consumed by TV4 (Agent) and TV2 (Cross-check)."""

    def solve(
        self,
        cnf: CNFFormula,
        assumptions: Sequence[int] = (),
    ) -> SATResult:
        """Run deterministic DPLL SAT solving on `cnf` with temporary unit assumptions."""
        ...


@runtime_checkable
class ILogicAgent(Protocol):
    """Port owned by TV4 (`agent/`), consumed by TV1 (Verdict validation) and TV5 (GUI).

    Receives ONLY `PublicState`; must never inspect hidden statuses or unrevealed clues.
    """

    def check_consistency(self, state: PublicState) -> bool:
        """Return True iff KB_t derived from `state` is satisfiable."""
        ...

    def classify_character(self, state: PublicState, cell: CellID) -> Status:
        """Classify `cell` via logical entailment: CRIMINAL, INNOCENT, or UNKNOWN."""
        ...

    def classify_all(self, state: PublicState) -> dict[CellID, Status]:
        """Classify every unsolved character in `state` via logical entailment."""
        ...

    def get_hint(self, state: PublicState) -> HintResult:
        """Identify one currently forced character and relevant revealed clues."""
        ...

    def run_auto_solve(self, engine: IGameEngine) -> list[DeductionStep]:
        """Run the no-guess deduction loop until SOLVED, AMBIGUOUS, or INCONSISTENT."""
        ...

    def check_uniqueness(
        self,
        clues: Sequence[Clue],
        grid_size: int,
    ) -> UniquenessResult:
        """Verify whether the complete clue set has a unique satisfying assignment."""
        ...
