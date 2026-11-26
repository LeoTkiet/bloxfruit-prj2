"""Deterministic region resolution and parameter validation (owned by TV2).

Supports the 4 core regions required by the project specification plus the 5
advanced region expressions used by the extension clues:

    ROW, COL, NEIGHBORS, EXPLICIT,
    INTERSECTION, COMMON_NEIGHBORS, CORNERS, BOUNDARY, BETWEEN

Every resolver returns a *sorted, distinct* list of CellIDs in row-major order.
This implementation is deliberately independent of `engine/` (Strict Directory
Ownership) but matches `engine.puzzle_validator.resolve_region_cells` exactly.
"""

from __future__ import annotations

from core.contracts.models import (
    CellID,
    RegionSpec,
    RegionType,
    all_cell_ids,
    col_letter_to_index,
    coords_to_cell_id,
    parse_cell_id,
)

__all__ = ["RegionResolutionError", "resolve_region_cells"]


class RegionResolutionError(ValueError):
    """Raised when a RegionSpec is malformed or out of grid bounds."""


def _validate_grid_size(grid_size: int) -> None:
    if not isinstance(grid_size, int) or isinstance(grid_size, bool):
        raise RegionResolutionError(f"grid_size must be an integer, got {grid_size!r}")
    if not (1 <= grid_size <= 26):
        raise RegionResolutionError(f"grid_size must be in [1, 26], got {grid_size}")


def _is_valid_cell(cell: CellID, grid_size: int) -> bool:
    try:
        row_idx, col_idx = parse_cell_id(cell)
    except (ValueError, TypeError):
        return False
    return 0 <= row_idx < grid_size and 0 <= col_idx < grid_size


def _require_valid_cell(cell: object, grid_size: int, context: str) -> CellID:
    if not isinstance(cell, str) or not _is_valid_cell(cell, grid_size):
        raise RegionResolutionError(
            f"Invalid cell {cell!r} for a {grid_size}x{grid_size} grid in {context}"
        )
    return cell


def _neighbors_of(cell: CellID, grid_size: int) -> list[CellID]:
    """Return the (up to) 8 edge/corner/diagonal neighbors, excluding `cell`."""
    row_idx, col_idx = parse_cell_id(cell)
    neighbors: list[CellID] = []
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            n_row, n_col = row_idx + d_row, col_idx + d_col
            if 0 <= n_row < grid_size and 0 <= n_col < grid_size:
                neighbors.append(coords_to_cell_id(n_row, n_col))
    return neighbors


def resolve_region_cells(region: RegionSpec, grid_size: int) -> list[CellID]:
    """Validate `region` and resolve it into deterministic row-major CellIDs.

    Distinctness and deterministic ordering are guaranteed for every region
    type, including compound expressions such as INTERSECTION and BETWEEN.
    """
    _validate_grid_size(grid_size)
    if not isinstance(region, RegionSpec):
        raise RegionResolutionError(f"region must be a RegionSpec, got {type(region).__name__}")

    order_index = {cid: idx for idx, cid in enumerate(all_cell_ids(grid_size))}
    region_type = region.region_type

    def ordered(cells: set[CellID] | list[CellID]) -> list[CellID]:
        return sorted(set(cells), key=lambda cid: order_index[cid])

    if region_type == RegionType.ROW:
        row = region.row
        if not isinstance(row, int) or isinstance(row, bool) or not (1 <= row <= grid_size):
            raise RegionResolutionError(
                f"ROW region row={row!r} out of range [1, {grid_size}]"
            )
        return [coords_to_cell_id(row - 1, col_idx) for col_idx in range(grid_size)]

    if region_type == RegionType.COL:
        col = region.col
        if not isinstance(col, str):
            raise RegionResolutionError(f"COL region missing/invalid column: {col!r}")
        try:
            col_idx = col_letter_to_index(col)
        except ValueError as exc:
            raise RegionResolutionError(f"Invalid COL letter {col!r}") from exc
        if not (0 <= col_idx < grid_size):
            raise RegionResolutionError(
                f"COL region col={col!r} out of bounds for {grid_size}x{grid_size}"
            )
        return [coords_to_cell_id(row_idx, col_idx) for row_idx in range(grid_size)]

    if region_type == RegionType.NEIGHBORS:
        center = _require_valid_cell(region.center, grid_size, "NEIGHBORS.center")
        return ordered(_neighbors_of(center, grid_size))

    if region_type == RegionType.EXPLICIT:
        if not region.cells:
            raise RegionResolutionError("EXPLICIT region must contain at least one cell")
        for cell in region.cells:
            _require_valid_cell(cell, grid_size, "EXPLICIT.cells")
        if len(set(region.cells)) != len(region.cells):
            raise RegionResolutionError(
                f"Duplicate cell in EXPLICIT region: {region.cells}"
            )
        return ordered(region.cells)

    if region_type == RegionType.CORNERS:
        if grid_size < 2:
            raise RegionResolutionError("CORNERS requires grid_size >= 2")
        corners = [
            coords_to_cell_id(0, 0),
            coords_to_cell_id(0, grid_size - 1),
            coords_to_cell_id(grid_size - 1, 0),
            coords_to_cell_id(grid_size - 1, grid_size - 1),
        ]
        return ordered(corners)

    if region_type == RegionType.BOUNDARY:
        if grid_size < 2:
            raise RegionResolutionError("BOUNDARY requires grid_size >= 2")
        boundary = [
            coords_to_cell_id(row_idx, col_idx)
            for row_idx in range(grid_size)
            for col_idx in range(grid_size)
            if row_idx in (0, grid_size - 1) or col_idx in (0, grid_size - 1)
        ]
        return ordered(boundary)

    if region_type == RegionType.COMMON_NEIGHBORS:
        if len(region.cells) != 2:
            raise RegionResolutionError(
                f"COMMON_NEIGHBORS requires exactly 2 cells, got {len(region.cells)}"
            )
        first = _require_valid_cell(region.cells[0], grid_size, "COMMON_NEIGHBORS[0]")
        second = _require_valid_cell(region.cells[1], grid_size, "COMMON_NEIGHBORS[1]")
        if first == second:
            raise RegionResolutionError(
                f"COMMON_NEIGHBORS requires 2 distinct cells, got {first!r} twice"
            )
        common = set(_neighbors_of(first, grid_size)) & set(
            _neighbors_of(second, grid_size)
        )
        return ordered(common)

    if region_type == RegionType.BETWEEN:
        if len(region.cells) != 2:
            raise RegionResolutionError(
                f"BETWEEN requires exactly 2 cells, got {len(region.cells)}"
            )
        first = _require_valid_cell(region.cells[0], grid_size, "BETWEEN[0]")
        second = _require_valid_cell(region.cells[1], grid_size, "BETWEEN[1]")
        if first == second:
            raise RegionResolutionError(f"BETWEEN requires 2 distinct cells, got {first!r}")
        row_a, col_a = parse_cell_id(first)
        row_b, col_b = parse_cell_id(second)
        if row_a == row_b:
            lo, hi = min(col_a, col_b), max(col_a, col_b)
            between = [coords_to_cell_id(row_a, col) for col in range(lo + 1, hi)]
        elif col_a == col_b:
            lo, hi = min(row_a, row_b), max(row_a, row_b)
            between = [coords_to_cell_id(row, col_a) for row in range(lo + 1, hi)]
        else:
            raise RegionResolutionError(
                f"BETWEEN endpoints {first!r} and {second!r} must share a row or column"
            )
        return ordered(between)

    if region_type == RegionType.INTERSECTION:
        if len(region.sub_regions) < 2:
            raise RegionResolutionError(
                "INTERSECTION requires at least 2 sub_regions"
            )
        resolved = [
            set(resolve_region_cells(sub, grid_size)) for sub in region.sub_regions
        ]
        return ordered(set.intersection(*resolved))

    raise RegionResolutionError(f"Unsupported region type: {region_type!r}")
