"""Puzzle structural validator & engine-local region resolver (owned by TV1).

Validates every puzzle JSON against the Griductive specification:
- Complete N x N grid covering A1..EN with no missing or duplicate cells
- Characters ordered alphabetically by display name in row-major order
- Valid hidden statuses (CRIMINAL or INNOCENT)
- Valid non-empty `initial_revealed` cell list
- Unique clue IDs and valid clue/region parameters (including 0 <= k <= |R|)

Also includes a CLI validator:
    python -m engine.puzzle_validator Source/puzzles
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional

from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CompareOp,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
    all_cell_ids,
    col_letter_to_index,
    coords_to_cell_id,
    parse_cell_id,
)
from engine.puzzle_loader import PuzzleDefinition, load_puzzle_definition


class PuzzleValidationError(ValueError):
    """Raised when a puzzle definition violates structural or domain constraints."""


def _is_valid_cell(cell: CellID, grid_size: int) -> bool:
    try:
        r, c = parse_cell_id(cell)
    except ValueError:
        return False
    return 0 <= r < grid_size and 0 <= c < grid_size


def _require_valid_cell(cell: Optional[CellID], grid_size: int, context: str) -> CellID:
    if not cell or not _is_valid_cell(cell, grid_size):
        raise PuzzleValidationError(
            f"Invalid cell {cell!r} for {grid_size}x{grid_size} grid in {context}"
        )
    return cell


def _neighbors_of(cell: CellID, grid_size: int) -> list[CellID]:
    r, c = parse_cell_id(cell)
    result: list[CellID] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                result.append(coords_to_cell_id(nr, nc))
    return result


def resolve_region_cells(region: RegionSpec, grid_size: int) -> list[CellID]:
    """Validate and resolve a `RegionSpec` into deterministic row-major distinct CellIDs.

    Used by `puzzle_validator` for parameter bounds (`0 <= k <= |R|`) and as a
    fallback highlighter in `GameEngine` when TV2's `ICNFEncoder` is not injected.
    """
    order_index = {cid: idx for idx, cid in enumerate(all_cell_ids(grid_size))}
    rt = region.region_type

    if rt == RegionType.ROW:
        if region.row is None or not (1 <= region.row <= grid_size):
            raise PuzzleValidationError(
                f"ROW region row={region.row!r} out of range [1, {grid_size}]"
            )
        r = region.row - 1
        return [coords_to_cell_id(r, c) for c in range(grid_size)]

    if rt == RegionType.COL:
        if not region.col:
            raise PuzzleValidationError("COL region missing column letter")
        try:
            c = col_letter_to_index(region.col)
        except ValueError as exc:
            raise PuzzleValidationError(f"Invalid COL letter {region.col!r}") from exc
        if not (0 <= c < grid_size):
            raise PuzzleValidationError(
                f"COL region col={region.col!r} out of range for {grid_size}x{grid_size}"
            )
        return [coords_to_cell_id(r, c) for r in range(grid_size)]

    if rt == RegionType.NEIGHBORS:
        center = _require_valid_cell(region.center, grid_size, "NEIGHBORS.center")
        cells = _neighbors_of(center, grid_size)
        return sorted(cells, key=lambda cid: order_index[cid])

    if rt == RegionType.EXPLICIT:
        if not region.cells:
            raise PuzzleValidationError("EXPLICIT region must contain at least one cell")
        seen: set[CellID] = set()
        for cid in region.cells:
            _require_valid_cell(cid, grid_size, "EXPLICIT.cells")
            if cid in seen:
                raise PuzzleValidationError(f"Duplicate cell {cid!r} in EXPLICIT region")
            seen.add(cid)
        return sorted(seen, key=lambda cid: order_index[cid])

    if rt == RegionType.CORNERS:
        if grid_size < 2:
            raise PuzzleValidationError("CORNERS requires grid_size >= 2")
        corners = [
            coords_to_cell_id(0, 0),
            coords_to_cell_id(0, grid_size - 1),
            coords_to_cell_id(grid_size - 1, 0),
            coords_to_cell_id(grid_size - 1, grid_size - 1),
        ]
        return sorted(corners, key=lambda cid: order_index[cid])

    if rt == RegionType.BOUNDARY:
        if grid_size < 2:
            raise PuzzleValidationError("BOUNDARY requires grid_size >= 2")
        boundary = [
            coords_to_cell_id(r, c)
            for r in range(grid_size)
            for c in range(grid_size)
            if r in (0, grid_size - 1) or c in (0, grid_size - 1)
        ]
        return boundary

    if rt == RegionType.COMMON_NEIGHBORS:
        if len(region.cells) != 2:
            raise PuzzleValidationError(
                f"COMMON_NEIGHBORS requires exactly 2 cells, got {len(region.cells)}"
            )
        c1 = _require_valid_cell(region.cells[0], grid_size, "COMMON_NEIGHBORS[0]")
        c2 = _require_valid_cell(region.cells[1], grid_size, "COMMON_NEIGHBORS[1]")
        if c1 == c2:
            raise PuzzleValidationError(
                f"COMMON_NEIGHBORS requires 2 distinct cells, got {c1!r} twice"
            )
        common = set(_neighbors_of(c1, grid_size)) & set(_neighbors_of(c2, grid_size))
        return sorted(common, key=lambda cid: order_index[cid])

    if rt == RegionType.BETWEEN:
        if len(region.cells) != 2:
            raise PuzzleValidationError(
                f"BETWEEN requires exactly 2 cells, got {len(region.cells)}"
            )
        c1 = _require_valid_cell(region.cells[0], grid_size, "BETWEEN[0]")
        c2 = _require_valid_cell(region.cells[1], grid_size, "BETWEEN[1]")
        if c1 == c2:
            raise PuzzleValidationError("BETWEEN requires 2 distinct cells")
        r1, col1 = parse_cell_id(c1)
        r2, col2 = parse_cell_id(c2)
        if r1 == r2:
            lo, hi = min(col1, col2), max(col1, col2)
            between = [coords_to_cell_id(r1, col) for col in range(lo + 1, hi)]
        elif col1 == col2:
            lo, hi = min(r1, r2), max(r1, r2)
            between = [coords_to_cell_id(row, col1) for row in range(lo + 1, hi)]
        else:
            raise PuzzleValidationError(
                f"BETWEEN endpoints {c1!r} and {c2!r} must share a row or column"
            )
        return sorted(between, key=lambda cid: order_index[cid])

    if rt == RegionType.INTERSECTION:
        if len(region.sub_regions) < 2:
            raise PuzzleValidationError(
                "INTERSECTION requires at least 2 sub_regions"
            )
        resolved_sets = [
            set(resolve_region_cells(sub, grid_size)) for sub in region.sub_regions
        ]
        inter = set.intersection(*resolved_sets)
        return sorted(inter, key=lambda cid: order_index[cid])

    raise PuzzleValidationError(f"Unsupported region type: {rt!r}")


def validate_region(region: RegionSpec, grid_size: int) -> list[CellID]:
    """Validate a `RegionSpec` and return its resolved CellIDs."""
    return resolve_region_cells(region, grid_size)


def validate_clue(clue: Clue, grid_size: int) -> None:
    """Validate a single structured `Clue` against grid bounds and semantics."""
    ctx = f"clue {clue.clue_id!r} (owner={clue.owner})"
    _require_valid_cell(clue.owner, grid_size, f"{ctx}.owner")

    ct = clue.clue_type
    if ct == ClueType.FACT:
        _require_valid_cell(clue.target, grid_size, f"{ctx}.target")
        if clue.target_status not in (Status.CRIMINAL, Status.INNOCENT):
            raise PuzzleValidationError(
                f"{ctx}: FACT target_status must be CRIMINAL or INNOCENT, "
                f"got {clue.target_status!r}"
            )
        return

    if ct in (ClueType.SAME, ClueType.DIFFERENT):
        if len(clue.targets) != 2:
            raise PuzzleValidationError(
                f"{ctx}: {ct.value} requires exactly 2 targets, got {len(clue.targets)}"
            )
        t1 = _require_valid_cell(clue.targets[0], grid_size, f"{ctx}.targets[0]")
        t2 = _require_valid_cell(clue.targets[1], grid_size, f"{ctx}.targets[1]")
        if t1 == t2:
            raise PuzzleValidationError(
                f"{ctx}: {ct.value} requires 2 distinct targets, got {t1!r} twice"
            )
        return

    if ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
        if clue.region is None:
            raise PuzzleValidationError(f"{ctx}: {ct.value} requires a region")
        cells = validate_region(clue.region, grid_size)
        if clue.count is None or not (0 <= clue.count <= len(cells)):
            raise PuzzleValidationError(
                f"{ctx}: {ct.value} count={clue.count!r} out of valid range [0, {len(cells)}]"
            )
        return

    if ct == ClueType.PARITY:
        if clue.region is None:
            raise PuzzleValidationError(f"{ctx}: PARITY requires a region")
        validate_region(clue.region, grid_size)
        if clue.parity not in (ParityKind.EVEN, ParityKind.ODD):
            raise PuzzleValidationError(f"{ctx}: PARITY requires EVEN or ODD")
        return

    if ct == ClueType.COMPARE_COUNTS:
        if clue.region is None or clue.region_b is None:
            raise PuzzleValidationError(
                f"{ctx}: COMPARE_COUNTS requires both region and region_b"
            )
        validate_region(clue.region, grid_size)
        validate_region(clue.region_b, grid_size)
        if clue.compare_op not in tuple(CompareOp):
            raise PuzzleValidationError(
                f"{ctx}: COMPARE_COUNTS invalid operator {clue.compare_op!r}"
            )
        return

    raise PuzzleValidationError(f"{ctx}: unsupported clue type {ct!r}")


def extract_clue_referenced_cells(
    clue: Clue,
    grid_size: int,
    region_resolver: Optional[Callable[[RegionSpec, int], list[CellID]]] = None,
) -> list[CellID]:
    """Return all distinct CellIDs referenced or counted by `clue` in row-major order."""
    resolver = region_resolver or resolve_region_cells
    order_index = {cid: idx for idx, cid in enumerate(all_cell_ids(grid_size))}
    cells: set[CellID] = set()

    if clue.clue_type == ClueType.FACT and clue.target is not None:
        cells.add(clue.target)
    elif clue.clue_type in (ClueType.SAME, ClueType.DIFFERENT):
        cells.update(clue.targets)
    elif clue.clue_type in (
        ClueType.EXACTLY,
        ClueType.AT_LEAST,
        ClueType.AT_MOST,
        ClueType.PARITY,
    ):
        if clue.region is not None:
            cells.update(resolver(clue.region, grid_size))
    elif clue.clue_type == ClueType.COMPARE_COUNTS:
        if clue.region is not None:
            cells.update(resolver(clue.region, grid_size))
        if clue.region_b is not None:
            cells.update(resolver(clue.region_b, grid_size))

    return sorted(cells, key=lambda cid: order_index[cid])


def validate_puzzle(puzzle: PuzzleDefinition) -> None:
    """Validate all structural and domain invariants of a loaded `PuzzleDefinition`."""
    n = puzzle.grid_size
    if not (2 <= n <= 26):
        raise PuzzleValidationError(f"grid_size must be in [2, 26], got {n}")

    expected_cells = all_cell_ids(n)
    actual_cells = tuple(c.cell_id for c in puzzle.characters)

    if len(puzzle.characters) != n * n:
        raise PuzzleValidationError(
            f"Expected {n * n} characters for {n}x{n} grid, got {len(puzzle.characters)}"
        )
    if set(actual_cells) != set(expected_cells):
        missing = sorted(set(expected_cells) - set(actual_cells))
        extra = sorted(set(actual_cells) - set(expected_cells))
        raise PuzzleValidationError(
            f"Character cells do not match {n}x{n} grid. Missing={missing}, Extra={extra}"
        )

    # Verify alphabetical ordering of character display names in row-major order
    # (Spec Section 2.1: "Characters are ordered alphabetically by display name.")
    names_lower = [c.name.casefold() for c in puzzle.characters]
    if names_lower != sorted(names_lower):
        raise PuzzleValidationError(
            "Characters must be ordered alphabetically by display name in row-major order: "
            f"{[c.name for c in puzzle.characters]}"
        )

    # Verify initial_revealed
    if not puzzle.initial_revealed:
        raise PuzzleValidationError("initial_revealed must contain at least one cell")
    if len(set(puzzle.initial_revealed)) != len(puzzle.initial_revealed):
        raise PuzzleValidationError("initial_revealed contains duplicate cells")
    for cid in puzzle.initial_revealed:
        _require_valid_cell(cid, n, "initial_revealed")

    # Verify each character & clue
    seen_clue_ids: set[str] = set()
    for ch in puzzle.characters:
        if ch.hidden_status not in (Status.CRIMINAL, Status.INNOCENT):
            raise PuzzleValidationError(
                f"Character {ch.cell_id} hidden_status must be CRIMINAL or INNOCENT, "
                f"got {ch.hidden_status!r}"
            )
        if ch.hidden_clue.owner != ch.cell_id:
            raise PuzzleValidationError(
                f"Clue {ch.hidden_clue.clue_id!r} owner {ch.hidden_clue.owner!r} "
                f"does not match character cell {ch.cell_id!r}"
            )
        if ch.hidden_clue.clue_id in seen_clue_ids:
            raise PuzzleValidationError(
                f"Duplicate clue_id {ch.hidden_clue.clue_id!r}"
            )
        seen_clue_ids.add(ch.hidden_clue.clue_id)
        validate_clue(ch.hidden_clue, n)


def _cli_main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python -m engine.puzzle_validator <puzzle.json | directory> [...]")
        return 2

    files: list[Path] = []
    for arg in argv[1:]:
        p = Path(arg)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        else:
            files.append(p)

    if not files:
        print("No JSON puzzle files found.")
        return 1

    failed = 0
    for f in files:
        try:
            puzzle = load_puzzle_definition(f)
            validate_puzzle(puzzle)
            print(f"[OK]   {f} ({puzzle.puzzle_id}, {puzzle.grid_size}x{puzzle.grid_size})")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {f}: {exc}")

    print(f"\nValidated {len(files)} puzzle(s): {len(files) - failed} passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_cli_main(sys.argv))
