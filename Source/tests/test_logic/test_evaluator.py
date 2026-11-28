"""Tests for TV2's direct semantic evaluator (ground-truth oracle)."""

from __future__ import annotations

import pytest

from core.contracts.interfaces import IDirectEvaluator
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
)
from logic.evaluator import DirectSemanticEvaluator, evaluate_cnf_clauses


def _assignment(cells: tuple[CellID, ...], grid_size: int = 3) -> dict[CellID, bool]:
    return {cell: cell in cells for cell in all_cell_ids(grid_size)}


def _clue(**kwargs) -> Clue:
    defaults = dict(clue_id="test", owner="A1", clue_type=ClueType.FACT, text="")
    defaults.update(kwargs)
    return Clue(**defaults)


def test_contract_compliance() -> None:
    assert isinstance(DirectSemanticEvaluator(), IDirectEvaluator)


def test_fact_and_binary_clues() -> None:
    evaluator = DirectSemanticEvaluator()
    assignment = _assignment(("A1", "C2"))

    fact_criminal = _clue(target="A1", target_status=Status.CRIMINAL)
    fact_innocent = _clue(target="A1", target_status=Status.INNOCENT)
    assert evaluator.evaluate_clue_direct(fact_criminal, assignment, 3) is True
    assert evaluator.evaluate_clue_direct(fact_innocent, assignment, 3) is False

    same = _clue(clue_id="same", clue_type=ClueType.SAME, targets=("A1", "C2"))
    different = _clue(
        clue_id="different", clue_type=ClueType.DIFFERENT, targets=("A1", "C2")
    )
    assert evaluator.evaluate_clue_direct(same, assignment, 3) is True
    assert evaluator.evaluate_clue_direct(different, assignment, 3) is False


def test_counting_and_parity_clues() -> None:
    evaluator = DirectSemanticEvaluator()
    assignment = _assignment(("A1", "B1"))
    region = RegionSpec(RegionType.EXPLICIT, cells=("A1", "B1", "C1"))

    exactly = _clue(
        clue_id="exactly", clue_type=ClueType.EXACTLY, region=region, count=2
    )
    at_least = _clue(
        clue_id="at_least", clue_type=ClueType.AT_LEAST, region=region, count=2
    )
    at_most = _clue(
        clue_id="at_most", clue_type=ClueType.AT_MOST, region=region, count=1
    )
    even = _clue(
        clue_id="even", clue_type=ClueType.PARITY, region=region, parity=ParityKind.EVEN
    )
    odd = _clue(
        clue_id="odd", clue_type=ClueType.PARITY, region=region, parity=ParityKind.ODD
    )
    assert evaluator.evaluate_clue_direct(exactly, assignment, 3) is True
    assert evaluator.evaluate_clue_direct(at_least, assignment, 3) is True
    assert evaluator.evaluate_clue_direct(at_most, assignment, 3) is False
    assert evaluator.evaluate_clue_direct(even, assignment, 3) is True
    assert evaluator.evaluate_clue_direct(odd, assignment, 3) is False


def test_compare_counts_all_operators() -> None:
    evaluator = DirectSemanticEvaluator()
    assignment = _assignment(("A1", "B2"))
    left = RegionSpec(RegionType.COL, col="A")
    right = RegionSpec(RegionType.ROW, row=2)

    for op, expected in (
        (CompareOp.EQ, True),
        (CompareOp.LT, False),
        (CompareOp.GT, False),
        (CompareOp.LE, True),
        (CompareOp.GE, True),
    ):
        clue = _clue(
            clue_id=f"cmp_{op.value}",
            clue_type=ClueType.COMPARE_COUNTS,
            region=left,
            region_b=right,
            compare_op=op,
        )
        assert evaluator.evaluate_clue_direct(clue, assignment, 3) is expected


def test_incomplete_assignment_is_rejected() -> None:
    evaluator = DirectSemanticEvaluator()
    clue = _clue(target="A1", target_status=Status.CRIMINAL)
    with pytest.raises(ValueError):
        evaluator.evaluate_clue_direct(clue, {"A1": True}, 3)


def test_direct_cnf_clause_checker() -> None:
    clauses = [[1, 2], [-1, 3]]
    assert evaluate_cnf_clauses(clauses, {1: True, 2: True, 3: True}) is True
    assert evaluate_cnf_clauses(clauses, {1: False, 2: True, 3: True}) is True
    assert evaluate_cnf_clauses(clauses, {1: False, 2: False, 3: True}) is False
    with pytest.raises(ValueError):
        evaluate_cnf_clauses([[1]], {})
