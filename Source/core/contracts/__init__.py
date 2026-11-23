"""Shared immutable data contracts and interfaces for Griductive Solver.

FROZEN CONTRACT (Phase 0 - TV1 leads, all 5 members review):
Any change to `models.py` or `interfaces.py` affects all 5 modules and must go
through a team-reviewed Pull Request.
"""

from core.contracts.interfaces import (
    ICNFEncoder,
    IDirectEvaluator,
    IGameEngine,
    ILogicAgent,
    ISATSolver,
)
from core.contracts.models import (
    CellID,
    CharacterPublicInfo,
    Clue,
    ClueType,
    CNFFormula,
    CNFStats,
    CompareOp,
    DeductionStep,
    HintResult,
    ParityKind,
    PublicState,
    RegionSpec,
    RegionType,
    SATMetrics,
    SATQueryLog,
    SATResult,
    Status,
    UniquenessResult,
    VerdictCode,
    VerdictResponse,
    all_cell_ids,
    col_index_to_letter,
    col_letter_to_index,
    coords_to_cell_id,
    parse_cell_id,
)

__all__ = [
    # Type aliases & coordinate helpers
    "CellID",
    "col_index_to_letter",
    "col_letter_to_index",
    "coords_to_cell_id",
    "parse_cell_id",
    "all_cell_ids",
    # Enums
    "Status",
    "VerdictCode",
    "RegionType",
    "ClueType",
    "ParityKind",
    "CompareOp",
    # Data models
    "RegionSpec",
    "Clue",
    "CharacterPublicInfo",
    "PublicState",
    "VerdictResponse",
    "CNFFormula",
    "CNFStats",
    "SATMetrics",
    "SATResult",
    "SATQueryLog",
    "DeductionStep",
    "HintResult",
    "UniquenessResult",
    # Interfaces
    "IGameEngine",
    "ICNFEncoder",
    "IDirectEvaluator",
    "ISATSolver",
    "ILogicAgent",
]
