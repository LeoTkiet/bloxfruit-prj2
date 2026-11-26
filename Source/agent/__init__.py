"""Deductive Logic Agent package (owned by TV4)."""

from agent.entailment import (
    EntailmentResult,
    check_kb_consistency,
    classify_board,
    classify_single_cell,
    sort_cells_row_major,
)
from agent.hint_engine import build_hint
from agent.kb_cache import KBCache, KBCacheEntry, KBKey, make_kb_key
from agent.logic_agent import AgentStats, DeductiveLogicAgent
from agent.outcome import AutoSolveOutcome, outcome_of
from agent.uniqueness import check_uniqueness

__all__ = [
    "AgentStats",
    "AutoSolveOutcome",
    "DeductiveLogicAgent",
    "EntailmentResult",
    "KBCache",
    "KBCacheEntry",
    "KBKey",
    "build_hint",
    "check_kb_consistency",
    "check_uniqueness",
    "classify_board",
    "classify_single_cell",
    "make_kb_key",
    "outcome_of",
    "sort_cells_row_major",
]
