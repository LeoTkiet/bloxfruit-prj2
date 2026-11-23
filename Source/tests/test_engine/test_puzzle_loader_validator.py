"""Unit tests for PuzzleLoader, PuzzleValidator, and region resolution."""

import json
from pathlib import Path

import pytest

from core.contracts.models import ClueType, RegionSpec, RegionType
from engine.puzzle_loader import PuzzleLoadError, load_puzzle_definition, parse_clue
from engine.puzzle_validator import (
    PuzzleValidationError,
    resolve_region_cells,
    validate_puzzle,
)


def test_resolve_core_and_extension_regions() -> None:
    # ROW & COL on 4x4
    assert resolve_region_cells(RegionSpec(RegionType.ROW, row=2), 4) == ["A2", "B2", "C2", "D2"]
    assert resolve_region_cells(RegionSpec(RegionType.COL, col="C"), 4) == ["C1", "C2", "C3", "C4"]

    # NEIGHBORS: corner=3, edge=5, interior=8 (self excluded)
    assert resolve_region_cells(RegionSpec(RegionType.NEIGHBORS, center="A1"), 4) == ["B1", "A2", "B2"]
    assert len(resolve_region_cells(RegionSpec(RegionType.NEIGHBORS, center="B1"), 4)) == 5
    interior = resolve_region_cells(RegionSpec(RegionType.NEIGHBORS, center="B2"), 4)
    assert len(interior) == 8
    assert "B2" not in interior

    # EXPLICIT
    assert resolve_region_cells(RegionSpec(RegionType.EXPLICIT, cells=("C3", "A1", "B2")), 4) == [
        "A1",
        "B2",
        "C3",
    ]

    # Extension 1: CORNERS, BOUNDARY, COMMON_NEIGHBORS, BETWEEN, INTERSECTION
    assert resolve_region_cells(RegionSpec(RegionType.CORNERS), 4) == ["A1", "D1", "A4", "D4"]
    assert len(resolve_region_cells(RegionSpec(RegionType.BOUNDARY), 4)) == 12
    assert resolve_region_cells(
        RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1", "C1")), 4
    ) == ["B1", "B2"]
    assert resolve_region_cells(
        RegionSpec(RegionType.BETWEEN, cells=("A1", "D1")), 4
    ) == ["B1", "C1"]
    assert resolve_region_cells(
        RegionSpec(RegionType.BETWEEN, cells=("B4", "B1")), 4
    ) == ["B2", "B3"]
    assert resolve_region_cells(
        RegionSpec(
            RegionType.INTERSECTION,
            sub_regions=(
                RegionSpec(RegionType.NEIGHBORS, center="B2"),
                RegionSpec(RegionType.ROW, row=1),
            ),
        ),
        4,
    ) == ["A1", "B1", "C1"]


def test_no_clue_alias_normalizes_to_exactly_zero() -> None:
    clue = parse_clue(
        {"clue_id": "c_no", "type": "NO", "region": {"type": "ROW", "row": 1}},
        owner="A1",
    )
    assert clue.clue_type == ClueType.EXACTLY
    assert clue.count == 0
    assert "No one" in clue.text


def test_validator_rejects_bad_regions_and_counts() -> None:
    with pytest.raises(PuzzleValidationError):
        resolve_region_cells(RegionSpec(RegionType.ROW, row=5), 4)
    with pytest.raises(PuzzleValidationError):
        resolve_region_cells(RegionSpec(RegionType.COL, col="E"), 4)
    with pytest.raises(PuzzleValidationError):
        resolve_region_cells(RegionSpec(RegionType.EXPLICIT, cells=("A1", "A1")), 4)
    with pytest.raises(PuzzleValidationError):
        resolve_region_cells(RegionSpec(RegionType.BETWEEN, cells=("A1", "C3")), 4)


def _minimal_valid_2x2_dict() -> dict:
    return {
        "puzzle_id": "test_2x2",
        "name": "Minimal 2x2",
        "grid_size": 2,
        "initial_revealed": ["A1"],
        "characters": [
            {
                "cell_id": "A1",
                "name": "Abel",
                "profession": "Cook",
                "status": "INNOCENT",
                "clue": {"clue_id": "c1", "type": "FACT", "target": "B1", "target_status": "CRIMINAL"},
            },
            {
                "cell_id": "B1",
                "name": "Bea",
                "profession": "Guard",
                "status": "CRIMINAL",
                "clue": {"clue_id": "c2", "type": "DIFFERENT", "targets": ["A2", "B2"]},
            },
            {
                "cell_id": "A2",
                "name": "Clara",
                "profession": "Clerk",
                "status": "CRIMINAL",
                "clue": {"clue_id": "c3", "type": "EXACTLY", "region": {"type": "ROW", "row": 2}, "count": 1},
            },
            {
                "cell_id": "B2",
                "name": "Derek",
                "profession": "Farmer",
                "status": "INNOCENT",
                "clue": {"clue_id": "c4", "type": "AT_MOST", "region": {"type": "COL", "col": "B"}, "count": 1},
            },
        ],
    }


def test_loader_and_validator_catch_invalid_puzzles(tmp_path: Path) -> None:
    # Missing file
    with pytest.raises(PuzzleLoadError):
        load_puzzle_definition(tmp_path / "missing.json")

    # Non-alphabetical character names
    bad_alpha = _minimal_valid_2x2_dict()
    bad_alpha["characters"][0]["name"] = "Zara"
    p1 = tmp_path / "bad_alpha.json"
    p1.write_text(json.dumps(bad_alpha), encoding="utf-8")
    with pytest.raises(PuzzleValidationError, match="alphabetically"):
        validate_puzzle(load_puzzle_definition(p1))

    # Count out of range (k > |R|)
    bad_count = _minimal_valid_2x2_dict()
    bad_count["characters"][2]["clue"]["count"] = 5
    p2 = tmp_path / "bad_count.json"
    p2.write_text(json.dumps(bad_count), encoding="utf-8")
    with pytest.raises(PuzzleValidationError, match="out of valid range"):
        validate_puzzle(load_puzzle_definition(p2))

    # Duplicate clue_id
    bad_dup_id = _minimal_valid_2x2_dict()
    bad_dup_id["characters"][1]["clue"]["clue_id"] = "c1"
    p3 = tmp_path / "bad_dup.json"
    p3.write_text(json.dumps(bad_dup_id), encoding="utf-8")
    with pytest.raises(PuzzleValidationError, match="Duplicate clue_id"):
        validate_puzzle(load_puzzle_definition(p3))

    # Empty initial_revealed
    bad_init = _minimal_valid_2x2_dict()
    bad_init["initial_revealed"] = []
    p4 = tmp_path / "bad_init.json"
    p4.write_text(json.dumps(bad_init), encoding="utf-8")
    with pytest.raises(PuzzleValidationError, match="initial_revealed"):
        validate_puzzle(load_puzzle_definition(p4))

    # Invalid JSON syntax
    p5 = tmp_path / "broken.json"
    p5.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(PuzzleLoadError, match="Invalid JSON"):
        load_puzzle_definition(p5)


def test_render_text_and_extract_cells_for_all_clue_types() -> None:
    from engine.puzzle_validator import _cli_main, extract_clue_referenced_cells

    clues = [
        parse_clue({"clue_id": "f1", "type": "FACT", "target": "A1", "target_status": "CRIMINAL"}, "A1"),
        parse_clue({"clue_id": "s1", "type": "SAME", "targets": ["A1", "B1"]}, "A1"),
        parse_clue({"clue_id": "d1", "type": "DIFFERENT", "targets": ["A1", "B2"]}, "A1"),
        parse_clue({"clue_id": "e1", "type": "EXACTLY", "region": {"type": "CORNERS"}, "count": 2}, "A1"),
        parse_clue({"clue_id": "al", "type": "AT_LEAST", "region": {"type": "BOUNDARY"}, "count": 1}, "A1"),
        parse_clue({"clue_id": "am", "type": "AT_MOST", "region": {"type": "NEIGHBORS", "center": "B2"}, "count": 3}, "A1"),
        parse_clue({"clue_id": "p1", "type": "PARITY", "region": {"type": "COMMON_NEIGHBORS", "cells": ["A1", "C1"]}, "parity": "ODD"}, "A1"),
        parse_clue({"clue_id": "p2", "type": "PARITY", "region": {"type": "BETWEEN", "cells": ["A1", "D1"]}, "parity": "EVEN"}, "A1"),
        parse_clue(
            {
                "clue_id": "cc",
                "type": "COMPARE_COUNTS",
                "region": {
                    "type": "INTERSECTION",
                    "sub_regions": [{"type": "ROW", "row": 1}, {"type": "EXPLICIT", "cells": ["A1", "B1", "A2"]}],
                },
                "region_b": {"type": "COL", "col": "C"},
                "compare_op": "GT",
            },
            "A1",
        ),
    ]
    for c in clues:
        assert c.text
        cells = extract_clue_referenced_cells(c, grid_size=4)
        assert len(cells) >= 1

    # Verify CLI validator returns 0 on Source/puzzles and 2 with no args
    puzzles_dir = Path(__file__).resolve().parents[2] / "puzzles"
    assert _cli_main(["puzzle_validator", str(puzzles_dir)]) == 0
    assert _cli_main(["puzzle_validator"]) == 2

