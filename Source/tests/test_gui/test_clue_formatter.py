"""Unit tests for natural-language formatting of all clue templates & regions."""

from __future__ import annotations

import pytest

from core.contracts.models import (
    Clue,
    ClueType,
    CompareOp,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
)
from gui.clue_formatter import format_clue, format_region


def test_format_clue_prefers_explicit_text() -> None:
    clue = Clue(
        clue_id="c1",
        owner="A1",
        clue_type=ClueType.FACT,
        target="B1",
        target_status=Status.CRIMINAL,
        text="  Custom narrative clue text.  ",
    )
    assert format_clue(clue) == "Custom narrative clue text."


def test_format_core_six_clue_templates() -> None:
    fact = Clue("c1", "A1", ClueType.FACT, target="B2", target_status=Status.CRIMINAL)
    assert format_clue(fact) == "B2 is Criminal."

    same = Clue("c2", "A1", ClueType.SAME, targets=("A2", "B2"))
    assert format_clue(same) == "A2 and B2 have the same status."

    diff = Clue("c3", "A1", ClueType.DIFFERENT, targets=("A2", "C3"))
    assert format_clue(diff) == "A2 and C3 have different statuses."

    row2 = RegionSpec(RegionType.ROW, row=2)
    zero = Clue("c4", "A1", ClueType.EXACTLY, region=row2, count=0)
    assert format_clue(zero) == "No Criminals in row 2."

    one = Clue("c5", "A1", ClueType.EXACTLY, region=row2, count=1)
    assert format_clue(one) == "Exactly 1 Criminal in row 2."

    at_least = Clue("c6", "A1", ClueType.AT_LEAST, region=row2, count=2)
    assert format_clue(at_least) == "At least 2 Criminals in row 2."

    at_most = Clue("c7", "A1", ClueType.AT_MOST, region=row2, count=1)
    assert format_clue(at_most) == "At most 1 Criminal in row 2."


@pytest.mark.parametrize(
    ("parity", "expected_word"),
    [(ParityKind.EVEN, "even"), (ParityKind.ODD, "odd")],
)
def test_format_parity_extension(parity: ParityKind, expected_word: str) -> None:
    clue = Clue(
        "cp",
        "A1",
        ClueType.PARITY,
        region=RegionSpec(RegionType.CORNERS),
        parity=parity,
    )
    assert format_clue(clue) == f"An {expected_word} number of Criminals in the 4 corners."


@pytest.mark.parametrize(
    ("op", "phrase"),
    [
        (CompareOp.EQ, "the same number of Criminals as"),
        (CompareOp.LT, "fewer Criminals than"),
        (CompareOp.GT, "more Criminals than"),
        (CompareOp.LE, "at most as many Criminals as"),
        (CompareOp.GE, "at least as many Criminals as"),
    ],
)
def test_format_compare_counts_extension(op: CompareOp, phrase: str) -> None:
    clue = Clue(
        "cc",
        "A1",
        ClueType.COMPARE_COUNTS,
        region=RegionSpec(RegionType.ROW, row=1),
        region_b=RegionSpec(RegionType.COL, col="C"),
        compare_op=op,
    )
    assert format_clue(clue) == f"Row 1 has {phrase} column C."


def test_format_all_region_types() -> None:
    assert format_region(RegionSpec(RegionType.ROW, row=3)) == "row 3"
    assert format_region(RegionSpec(RegionType.COL, col="B")) == "column B"
    assert format_region(RegionSpec(RegionType.NEIGHBORS, center="B2")) == "neighbors of B2"
    assert format_region(RegionSpec(RegionType.EXPLICIT, cells=("A1", "C3"))) == "{A1, C3}"
    assert format_region(RegionSpec(RegionType.CORNERS)) == "the 4 corners"
    assert format_region(RegionSpec(RegionType.BOUNDARY)) == "the boundary"
    assert (
        format_region(RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1", "C1")))
        == "common neighbors of A1 & C1"
    )
    assert (
        format_region(RegionSpec(RegionType.BETWEEN, cells=("A1", "A4")))
        == "cells between A1 and A4"
    )
    inter = RegionSpec(
        RegionType.INTERSECTION,
        sub_regions=(
            RegionSpec(RegionType.ROW, row=2),
            RegionSpec(RegionType.BOUNDARY),
        ),
    )
    assert format_region(inter) == "(row 2 ∩ the boundary)"
