"""Immutable shared data contracts for Griductive Solver.

This module defines every cross-module data structure used by:
- TV1 (`engine/`, `puzzles/`)
- TV2 (`logic/`)
- TV3 (`solver/`)
- TV4 (`agent/`, `experiments/`)
- TV5 (`gui/`, `main.py`)

Architectural invariant:
`PublicState` and `CharacterPublicInfo` NEVER store hidden character statuses
or unrevealed clues. All mappings exposed by frozen dataclasses are wrapped in
`MappingProxyType` to prevent accidental mutation across module boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional

CellID = str


# ---------------------------------------------------------------------------
# Deterministic grid coordinate helpers (0-based indices <-> 'A1'..'E5')
# ---------------------------------------------------------------------------


def col_index_to_letter(col_idx: int) -> str:
    """Convert 0-based column index (0 -> 'A', 1 -> 'B', ...) to letter."""
    if not (0 <= col_idx < 26):
        raise ValueError(f"Column index out of range [0, 25]: {col_idx}")
    return chr(ord("A") + col_idx)


def col_letter_to_index(letter: str) -> int:
    """Convert single uppercase column letter ('A' -> 0, 'B' -> 1, ...) to index."""
    if len(letter) != 1 or not ("A" <= letter <= "Z"):
        raise ValueError(f"Invalid column letter: {letter!r}")
    return ord(letter) - ord("A")


def coords_to_cell_id(row_idx: int, col_idx: int) -> CellID:
    """Convert 0-based (row_idx, col_idx) into canonical CellID (e.g. (1, 2) -> 'C2')."""
    if row_idx < 0:
        raise ValueError(f"Row index must be >= 0, got {row_idx}")
    return f"{col_index_to_letter(col_idx)}{row_idx + 1}"


def parse_cell_id(cell_id: CellID) -> tuple[int, int]:
    """Parse canonical CellID (e.g. 'C2') into 0-based (row_idx, col_idx) = (1, 2)."""
    if not isinstance(cell_id, str) or len(cell_id) < 2:
        raise ValueError(f"Invalid CellID: {cell_id!r}")
    col_letter = cell_id[0]
    row_str = cell_id[1:]
    if not ("A" <= col_letter <= "Z") or not row_str.isdigit():
        raise ValueError(f"Invalid CellID format: {cell_id!r}")
    row_num = int(row_str)
    if row_num < 1:
        raise ValueError(f"Row number must be >= 1 in CellID: {cell_id!r}")
    return row_num - 1, col_letter_to_index(col_letter)


def all_cell_ids(grid_size: int) -> tuple[CellID, ...]:
    """Return all CellIDs for an N x N grid in deterministic row-major order.

    Example for N=3: ('A1', 'B1', 'C1', 'A2', 'B2', 'C2', 'A3', 'B3', 'C3').
    """
    if grid_size < 1 or grid_size > 26:
        raise ValueError(f"Grid size must be in [1, 26], got {grid_size}")
    return tuple(
        coords_to_cell_id(r, c)
        for r in range(grid_size)
        for c in range(grid_size)
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Status(str, Enum):
    """Logical verdict / character status."""

    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"


class VerdictCode(str, Enum):
    """Outcome of submitting a verdict to the Game Engine."""

    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"
    INCONSISTENT = "INCONSISTENT"


class RegionType(str, Enum):
    """Supported clue regions (4 core + 5 advanced region expressions)."""

    # Core 4 required regions
    ROW = "ROW"
    COL = "COL"
    NEIGHBORS = "NEIGHBORS"
    EXPLICIT = "EXPLICIT"

    # Extension 1: Advanced region expressions
    INTERSECTION = "INTERSECTION"
    COMMON_NEIGHBORS = "COMMON_NEIGHBORS"
    CORNERS = "CORNERS"
    BOUNDARY = "BOUNDARY"
    BETWEEN = "BETWEEN"


class ClueType(str, Enum):
    """Supported structured clue templates (6 core + extensions)."""

    # Core 6 required clue templates
    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"

    # Extension 2: Parity constraint (EVEN / ODD number of Criminals in region)
    PARITY = "PARITY"

    # Extension 3 (optional): Compare Criminal counts across two regions
    COMPARE_COUNTS = "COMPARE_COUNTS"


class ParityKind(str, Enum):
    """Parity target for PARITY clues."""

    EVEN = "EVEN"
    ODD = "ODD"


class CompareOp(str, Enum):
    """Comparison operator for COMPARE_COUNTS clues (count(region) <op> count(region_b))."""

    EQ = "EQ"
    LT = "LT"
    GT = "GT"
    LE = "LE"
    GE = "GE"


# ---------------------------------------------------------------------------
# Clue & Region Specifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegionSpec:
    """Structured specification of a board region referenced by a clue.

    Field usage by `region_type`:
    - ROW: `row` (1-based row number, e.g. 2 for row 2)
    - COL: `col` (uppercase column letter, e.g. 'C')
    - NEIGHBORS: `center` (CellID whose 8-directional neighbors are selected)
    - EXPLICIT: `cells` (tuple of distinct CellIDs)
    - INTERSECTION: `sub_regions` (tuple of >= 2 RegionSpecs whose cells intersect)
    - COMMON_NEIGHBORS: `cells` (tuple of exactly 2 distinct CellIDs)
    - CORNERS: no parameters needed (the 4 corner cells of the N x N grid)
    - BOUNDARY: no parameters needed (all outer perimeter cells of the N x N grid)
    - BETWEEN: `cells` (tuple of exactly 2 CellIDs in the same row or same column;
      selects cells strictly between them)
    """

    region_type: RegionType
    row: Optional[int] = None
    col: Optional[str] = None
    center: Optional[CellID] = None
    cells: tuple[CellID, ...] = ()
    sub_regions: tuple["RegionSpec", ...] = ()


@dataclass(frozen=True)
class Clue:
    """Immutable structured clue owned by a character card.

    Field usage by `clue_type`:
    - FACT: `target` (CellID), `target_status` (CRIMINAL or INNOCENT)
    - SAME / DIFFERENT: `targets` (tuple of 2 distinct CellIDs)
    - EXACTLY / AT_LEAST / AT_MOST: `region` (RegionSpec), `count` (int k, 0 <= k <= |R|)
    - PARITY: `region` (RegionSpec), `parity` (EVEN or ODD)
    - COMPARE_COUNTS: `region` (left RegionSpec), `region_b` (right RegionSpec),
      `compare_op` (CompareOp)
    """

    clue_id: str
    owner: CellID
    clue_type: ClueType
    target: Optional[CellID] = None
    target_status: Optional[Status] = None
    targets: tuple[CellID, ...] = ()
    region: Optional[RegionSpec] = None
    region_b: Optional[RegionSpec] = None
    count: Optional[int] = None
    parity: Optional[ParityKind] = None
    compare_op: Optional[CompareOp] = None
    text: str = ""


# ---------------------------------------------------------------------------
# Public Game State (strictly isolated from hidden statuses & face-down clues)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CharacterPublicInfo:
    """Publicly visible information for a single character on the board."""

    cell_id: CellID
    name: str
    profession: str
    status: Status
    is_revealed: bool
    clue: Optional[Clue] = None

    def __post_init__(self) -> None:
        if not self.is_revealed:
            if self.status != Status.UNKNOWN:
                raise ValueError(
                    f"Unrevealed character {self.cell_id} must have UNKNOWN status, "
                    f"got {self.status}"
                )
            if self.clue is not None:
                raise ValueError(
                    f"Unrevealed character {self.cell_id} must not expose a clue"
                )
        else:
            if self.status not in (Status.CRIMINAL, Status.INNOCENT):
                raise ValueError(
                    f"Revealed character {self.cell_id} must be CRIMINAL or INNOCENT, "
                    f"got {self.status}"
                )


@dataclass(frozen=True)
class PublicState:
    """Immutable snapshot of the public knowledge base state at step `t`.

    Contains ONLY revealed cards, their clues, and proved verdicts.
    No hidden solution or unrevealed clue is reachable from this object.
    """

    puzzle_id: str
    puzzle_name: str
    grid_size: int
    step: int
    characters: tuple[CharacterPublicInfo, ...]
    proved_verdicts: Mapping[CellID, Status]
    revealed_clues: tuple[Clue, ...]
    is_solved: bool

    def __post_init__(self) -> None:
        # Freeze mapping to prevent external mutation
        object.__setattr__(
            self,
            "proved_verdicts",
            MappingProxyType(dict(self.proved_verdicts)),
        )

    @property
    def unsolved_cells(self) -> tuple[CellID, ...]:
        """Return unsolved CellIDs in deterministic row-major order."""
        return tuple(c.cell_id for c in self.characters if not c.is_revealed)

    @property
    def revealed_cells(self) -> tuple[CellID, ...]:
        """Return revealed CellIDs in deterministic row-major order."""
        return tuple(c.cell_id for c in self.characters if c.is_revealed)

    def get_character(self, cell_id: CellID) -> CharacterPublicInfo:
        """Look up a character's public info by CellID."""
        for char in self.characters:
            if char.cell_id == cell_id:
                return char
        raise KeyError(f"Unknown cell_id: {cell_id!r}")


@dataclass(frozen=True)
class VerdictResponse:
    """Response returned by `IGameEngine.submit_verdict`."""

    code: VerdictCode
    cell: CellID
    submitted_status: Status
    public_state: PublicState
    revealed_clue: Optional[Clue] = None
    message: str = ""


# ---------------------------------------------------------------------------
# CNF, SAT Solver, Deduction Agent, Hint, and Uniqueness Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CNFFormula:
    """CNF formula produced automatically by `ICNFEncoder`.

    Primary variables are indexed `1 .. num_primary_vars`.
    Auxiliary variables are indexed `num_primary_vars + 1 .. num_primary_vars + num_aux_vars`.
    """

    clauses: tuple[tuple[int, ...], ...]
    num_primary_vars: int
    num_aux_vars: int = 0
    var_to_cell: Mapping[int, CellID] = field(default_factory=dict)
    cell_to_var: Mapping[CellID, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "var_to_cell", MappingProxyType(dict(self.var_to_cell)))
        object.__setattr__(self, "cell_to_var", MappingProxyType(dict(self.cell_to_var)))

    @property
    def num_vars(self) -> int:
        return self.num_primary_vars + self.num_aux_vars

    @property
    def num_clauses(self) -> int:
        return len(self.clauses)


@dataclass(frozen=True)
class CNFStats:
    """Statistics reported by the CNF encoder for a knowledge base or puzzle."""

    num_primary_vars: int
    num_aux_vars: int
    num_clauses: int
    encoding_strategy: str = "direct"


@dataclass(frozen=True)
class SATMetrics:
    """Performance metrics recorded for a single DPLL SAT solver invocation."""

    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_ms: float = 0.0


@dataclass(frozen=True)
class SATResult:
    """Result returned by `ISATSolver.solve`."""

    is_sat: bool
    model: Optional[Mapping[int, bool]] = None
    metrics: SATMetrics = field(default_factory=SATMetrics)

    def __post_init__(self) -> None:
        if self.model is not None:
            object.__setattr__(self, "model", MappingProxyType(dict(self.model)))


@dataclass(frozen=True)
class SATQueryLog:
    """Audit record of a single SAT entailment query inside a deduction step."""

    cell: CellID
    assumptions: tuple[int, ...]
    is_sat: bool
    metrics: SATMetrics
    cached: bool = False


@dataclass(frozen=True)
class DeductionStep:
    """Trace record produced by the Deductive Logic Agent at step `t`."""

    step_number: int
    active_clue_ids: tuple[str, ...]
    sat_queries: tuple[SATQueryLog, ...]
    cell: Optional[CellID]
    verdict: Status
    verdict_code: VerdictCode
    revealed_clue: Optional[Clue] = None
    cnf_stats: Optional[CNFStats] = None


@dataclass(frozen=True)
class HintResult:
    """Hint computed strictly from the public knowledge state (never hidden data)."""

    cell: Optional[CellID]
    forced_status: Status
    relevant_clue_ids: tuple[str, ...] = ()
    message: str = ""
    is_inconsistent: bool = False


@dataclass(frozen=True)
class UniquenessResult:
    """Result of checking whether a complete clue set admits exactly one assignment."""

    is_unique: bool
    solution_count_status: str  # "UNIQUE", "UNSAT", or "MULTIPLE"
    first_model: Optional[Mapping[CellID, Status]] = None
    second_model: Optional[Mapping[CellID, Status]] = None
    metrics_first: Optional[SATMetrics] = None
    metrics_second: Optional[SATMetrics] = None

    def __post_init__(self) -> None:
        if self.first_model is not None:
            object.__setattr__(
                self, "first_model", MappingProxyType(dict(self.first_model))
            )
        if self.second_model is not None:
            object.__setattr__(
                self, "second_model", MappingProxyType(dict(self.second_model))
            )
