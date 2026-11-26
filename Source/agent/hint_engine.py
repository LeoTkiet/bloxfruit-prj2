"""Public-knowledge hint generation for Griductive Solver."""

from __future__ import annotations

from collections import deque
from typing import Callable, Mapping, Optional

from agent.entailment import sort_cells_row_major
from core.contracts.interfaces import ICNFEncoder
from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    HintResult,
    PublicState,
    Status,
)


def _clue_scope_cells(
    clue: Clue,
    grid_size: int,
    encoder: ICNFEncoder,
) -> set[CellID]:
    """Extract all CellIDs referenced by `clue` via `encoder.resolve_region`."""
    cells: set[CellID] = set()
    ct = clue.clue_type
    if ct == ClueType.FACT and clue.target is not None:
        cells.add(clue.target)
    elif ct in (ClueType.SAME, ClueType.DIFFERENT):
        cells.update(clue.targets)
    elif ct in (
        ClueType.EXACTLY,
        ClueType.AT_LEAST,
        ClueType.AT_MOST,
        ClueType.PARITY,
    ):
        if clue.region is not None:
            cells.update(encoder.resolve_region(clue.region, grid_size))
    elif ct == ClueType.COMPARE_COUNTS:
        if clue.region is not None:
            cells.update(encoder.resolve_region(clue.region, grid_size))
        if clue.region_b is not None:
            cells.update(encoder.resolve_region(clue.region_b, grid_size))
    return cells


def _collect_relevant_clues_for_cell(
    target_cell: CellID,
    state: PublicState,
    encoder: ICNFEncoder,
) -> tuple[str, ...]:
    """Find revealed clue IDs whose scope covers `target_cell` or linked unsolved cells."""
    unsolved_set = set(state.unsolved_cells)
    clue_scopes: list[tuple[str, set[CellID]]] = [
        (clue.clue_id, _clue_scope_cells(clue, state.grid_size, encoder))
        for clue in state.revealed_clues
    ]

    visited_cells: set[CellID] = {target_cell}
    queue: deque[CellID] = deque([target_cell])
    relevant_ids: set[str] = set()

    while queue:
        cell = queue.popleft()
        for clue_id, scope in clue_scopes:
            if cell in scope:
                relevant_ids.add(clue_id)
                for other in scope:
                    if other in unsolved_set and other not in visited_cells:
                        visited_cells.add(other)
                        queue.append(other)

    ordered = tuple(
        clue.clue_id
        for clue in state.revealed_clues
        if clue.clue_id in relevant_ids
    )
    if not ordered and state.revealed_clues:
        return tuple(c.clue_id for c in state.revealed_clues)
    return ordered


def _collect_clues_for_unsolved(
    state: PublicState,
    encoder: ICNFEncoder,
) -> tuple[str, ...]:
    """Find revealed clue IDs whose scope touches at least one unsolved cell."""
    unsolved_set = set(state.unsolved_cells)
    return tuple(
        clue.clue_id
        for clue in state.revealed_clues
        if _clue_scope_cells(clue, state.grid_size, encoder) & unsolved_set
    )


def build_hint(
    state: PublicState,
    encoder: ICNFEncoder,
    classify_fn: Callable[[PublicState], tuple[bool, Mapping[CellID, Status]]],
) -> HintResult:
    """Compute a `HintResult` strictly from `state` without reading hidden data."""
    if state.is_solved or not state.unsolved_cells:
        return HintResult(
            cell=None,
            forced_status=Status.UNKNOWN,
            relevant_clue_ids=(),
            message="Bảng đã được giải hoàn toàn.",
            is_inconsistent=False,
        )

    consistent, classification = classify_fn(state)
    if not consistent:
        return HintResult(
            cell=None,
            forced_status=Status.UNKNOWN,
            relevant_clue_ids=(),
            message="Cơ sở tri thức mâu thuẫn (INCONSISTENT).",
            is_inconsistent=True,
        )

    ordered_unsolved = sort_cells_row_major(state.unsolved_cells)
    chosen: Optional[tuple[CellID, Status]] = None
    for cid in ordered_unsolved:
        st = classification.get(cid, Status.UNKNOWN)
        if st in (Status.CRIMINAL, Status.INNOCENT):
            chosen = (cid, st)
            break

    if chosen is not None:
        target_cell, forced_status = chosen
        relevant_ids = _collect_relevant_clues_for_cell(target_cell, state, encoder)
        status_label = (
            "Tội phạm (CRIMINAL)"
            if forced_status == Status.CRIMINAL
            else "Vô tội (INNOCENT)"
        )
        if relevant_ids:
            msg = (
                f"Ô {target_cell} bắt buộc là {status_label} "
                f"dựa trên các manh mối: {', '.join(relevant_ids)}."
            )
        else:
            msg = f"Ô {target_cell} bắt buộc là {status_label}."
        return HintResult(
            cell=target_cell,
            forced_status=forced_status,
            relevant_clue_ids=relevant_ids,
            message=msg,
            is_inconsistent=False,
        )

    relevant_ids = _collect_clues_for_unsolved(state, encoder)
    if relevant_ids:
        msg = (
            "Không có nhân vật nào được suy ra chắc chắn từ các manh mối hiện có (AMBIGUOUS). "
            f"Hãy xem lại các manh mối: {', '.join(relevant_ids)}."
        )
    else:
        msg = "Không có nhân vật nào được suy ra chắc chắn từ các manh mối hiện có (AMBIGUOUS)."
    return HintResult(
        cell=None,
        forced_status=Status.UNKNOWN,
        relevant_clue_ids=relevant_ids,
        message=msg,
        is_inconsistent=False,
    )
