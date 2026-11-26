"""Tests for TV2's deterministic region resolver (core + advanced regions)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.contracts.models import RegionSpec, RegionType
from engine.puzzle_loader import load_puzzle_definition
from engine.puzzle_validator import resolve_region_cells as tv1_resolve
from logic.region_resolver import RegionResolutionError, resolve_region_cells


def test_core_row_and_column_regions() -> None:
    assert resolve_region_cells(RegionSpec(RegionType.ROW, row=2), 3) == [
        "A2",
        "B2",
        "C2",
    ]
    assert resolve_region_cells(RegionSpec(RegionType.COL, col="B"), 3) == [
        "B1",
        "B2",
        "B3",
    ]


def test_neighbors_exclude_center_and_are_row_major() -> None:
    assert resolve_region_cells(RegionSpec(RegionType.NEIGHBORS, center="B2"), 3) == [
        "A1",
        "B1",
        "C1",
        "A2",
        "C2",
        "A3",
        "B3",
        "C3",
    ]
    assert resolve_region_cells(RegionSpec(RegionType.NEIGHBORS, center="A1"), 3) == [
        "B1",
        "A2",
        "B2",
    ]


def test_explicit_region_is_sorted_and_distinct() -> None:
    region = RegionSpec(RegionType.EXPLICIT, cells=("C2", "A1", "B1"))
    assert resolve_region_cells(region, 3) == ["A1", "B1", "C2"]


def test_advanced_region_expressions() -> None:
    assert resolve_region_cells(RegionSpec(RegionType.CORNERS), 3) == [
        "A1",
        "C1",
        "A3",
        "C3",
    ]
    assert resolve_region_cells(RegionSpec(RegionType.BOUNDARY), 3) == [
        "A1",
        "B1",
        "C1",
        "A2",
        "C2",
        "A3",
        "B3",
        "C3",
    ]
    assert resolve_region_cells(
        RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1", "C1")), 3
    ) == ["B1", "B2"]
    assert resolve_region_cells(
        RegionSpec(RegionType.BETWEEN, cells=("A1", "C1")), 3
    ) == ["B1"]
    assert resolve_region_cells(
        RegionSpec(RegionType.BETWEEN, cells=("A1", "B1")), 3
    ) == []

    intersection = RegionSpec(
        RegionType.INTERSECTION,
        sub_regions=(
            RegionSpec(RegionType.NEIGHBORS, center="B2"),
            RegionSpec(RegionType.COL, col="B"),
        ),
    )
    assert resolve_region_cells(intersection, 3) == ["B1", "B3"]


@pytest.mark.parametrize(
    "region",
    [
        RegionSpec(RegionType.ROW, row=0),
        RegionSpec(RegionType.ROW, row=4),
        RegionSpec(RegionType.COL, col="D"),
        RegionSpec(RegionType.COL, col="ab"),
        RegionSpec(RegionType.NEIGHBORS, center="D2"),
        RegionSpec(RegionType.EXPLICIT, cells=()),
        RegionSpec(RegionType.EXPLICIT, cells=("A1", "A1")),
        RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1",)),
        RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1", "A1")),
        RegionSpec(RegionType.BETWEEN, cells=("A1", "C2")),
        RegionSpec(RegionType.INTERSECTION, sub_regions=(RegionSpec(RegionType.ROW, row=1),)),
    ],
)
def test_invalid_regions_are_rejected(region: RegionSpec) -> None:
    with pytest.raises(RegionResolutionError):
        resolve_region_cells(region, 3)


def _iter_regions(clue):
    if clue.region is not None:
        yield clue.region
        yield from _iter_sub_regions(clue.region)
    if clue.region_b is not None:
        yield clue.region_b
        yield from _iter_sub_regions(clue.region_b)


def _iter_sub_regions(region: RegionSpec):
    for sub in region.sub_regions:
        yield sub
        yield from _iter_sub_regions(sub)


def test_tv2_resolver_matches_tv1_on_every_puzzle_region() -> None:
    puzzle_dir = Path(__file__).resolve().parents[2] / "puzzles"
    puzzle_files = sorted(puzzle_dir.rglob("*.json"))
    assert len(puzzle_files) >= 15

    checked = 0
    for path in puzzle_files:
        puzzle = load_puzzle_definition(path)
        for character in puzzle.characters:
            for region in _iter_regions(character.hidden_clue):
                tv2 = resolve_region_cells(region, puzzle.grid_size)
                tv1 = tv1_resolve(region, puzzle.grid_size)
                assert tv2 == tv1, (path.name, character.cell_id, region, tv2, tv1)
                checked += 1
    assert checked > 50
