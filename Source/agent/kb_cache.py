"""LRU knowledge-base cache keyed by public KB state fingerprint."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from core.contracts.models import (
    CellID,
    CNFFormula,
    CNFStats,
    PublicState,
    SATQueryLog,
    Status,
)

KBKey = tuple[Any, ...]


def make_kb_key(state: PublicState) -> KBKey:
    """Build a deterministic hashable fingerprint for `state`'s public KB_t.

    Two `PublicState` snapshots with the same puzzle, grid size, revealed clues,
    and proved verdicts produce the same key.
    """
    return (
        state.puzzle_id,
        state.grid_size,
        frozenset(state.revealed_clues),
        frozenset(state.proved_verdicts.items()),
    )


@dataclass
class KBCacheEntry:
    """Cached entailment/consistency state for a single KB_t."""

    consistent: bool
    cnf: CNFFormula
    cnf_stats: CNFStats
    classification: dict[CellID, Status] = field(default_factory=dict)
    fully_classified: bool = False
    sat_queries: tuple[SATQueryLog, ...] = ()
    models: list[Mapping[int, bool]] = field(default_factory=list)
    initial_query: Optional[SATQueryLog] = None


class KBCache:
    """Bounded LRU cache (default maxsize=8) storing entailment results per KB_t."""

    def __init__(self, maxsize: int = 8) -> None:
        if maxsize < 1:
            raise ValueError(f"KBCache maxsize must be >= 1, got {maxsize}")
        self._maxsize = maxsize
        self._store: OrderedDict[KBKey, KBCacheEntry] = OrderedDict()

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def get(self, key: KBKey) -> Optional[KBCacheEntry]:
        entry = self._store.get(key)
        if entry is not None:
            self._store.move_to_end(key)
        return entry

    def put(self, key: KBKey, entry: KBCacheEntry) -> None:
        self._store[key] = entry
        self._store.move_to_end(key)
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
