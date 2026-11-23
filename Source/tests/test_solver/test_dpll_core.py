"""Tests for the 6 core DPLL features: Unit Propagation, Conflict Detection,
Deterministic Branching, Backtracking, SAT/UNSAT Output, and Assumptions.
"""

from __future__ import annotations

import pytest
from core.contracts.models import CNFFormula
from solver.dpll_solver import DPLLSolver
from solver.heuristics import DPLLConfig


def test_unit_propagation_single_and_chain() -> None:
    """Test unit propagation cascades across multiple unit clauses."""
    solver = DPLLSolver()
    # [1], [-1, 2], [-2, 3], [-3, 4] -> Forces 1=True, 2=True, 3=True, 4=True
    cnf = CNFFormula(
        clauses=((1,), (-1, 2), (-2, 3), (-3, 4)),
        num_primary_vars=4,
    )
    result = solver.solve(cnf)
    assert result.is_sat is True
    assert result.model is not None
    assert result.model[1] is True
    assert result.model[2] is True
    assert result.model[3] is True
    assert result.model[4] is True
    assert result.metrics.decisions == 0  # No branching needed
    assert result.metrics.propagations == 4


def test_conflict_detection_immediate_empty_clause() -> None:
    """Conflict detection should immediately identify an empty clause."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((),), num_primary_vars=1)
    result = solver.solve(cnf)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks == 1


def test_conflict_detection_unit_contradiction() -> None:
    """Contradictory unit clauses trigger unit propagation conflict."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1,), (-1,)), num_primary_vars=1)
    result = solver.solve(cnf)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks >= 1


def test_recursive_branching_and_backtracking_sat() -> None:
    """Formulas requiring branching find satisfying assignments through backtracking.

    With default_polarity=False, solver branches 1=False first:
    - (-1 or 2) with 1=False is satisfied.
    - (1 or 2) with 1=False forces 2=True (unit prop).
    - (1 or -2) with 1=False, 2=True becomes empty clause -> conflict! Backtracks.
    Then branches 1=True, satisfying the formula.
    """
    solver = DPLLSolver(DPLLConfig(default_polarity=False))
    cnf = CNFFormula(clauses=((1, 2), (-1, 2), (1, -2)), num_primary_vars=2)
    result = solver.solve(cnf)
    assert result.is_sat is True
    assert result.model is not None
    assert result.model[1] is True
    assert result.model[2] is True
    assert result.metrics.decisions >= 1
    assert result.metrics.backtracks >= 1  # Verified backtrack occurred!


def test_recursive_branching_and_backtracking_unsat() -> None:
    """All 4 combinations of 2 variables are forbidden -> UNSAT after full exploration."""
    solver = DPLLSolver()
    cnf = CNFFormula(
        clauses=((1, 2), (1, -2), (-1, 2), (-1, -2)),
        num_primary_vars=2,
    )
    result = solver.solve(cnf)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks >= 1


def test_assumptions_handling_non_destructive() -> None:
    """Assumptions temporarily constrain the search without modifying the formula."""
    solver = DPLLSolver()
    # Formula: (C1 or C2)
    cnf = CNFFormula(clauses=((1, 2),), num_primary_vars=2)

    # Under assumption C1 = False (-1), C2 must be True
    res_neg1 = solver.solve(cnf, assumptions=[-1])
    assert res_neg1.is_sat is True
    assert res_neg1.model is not None
    assert res_neg1.model[1] is False
    assert res_neg1.model[2] is True

    # Under contradictory assumptions: [-1, -2] -> UNSAT
    res_both_false = solver.solve(cnf, assumptions=[-1, -2])
    assert res_both_false.is_sat is False

    # Original formula remains SAT without assumptions
    res_base = solver.solve(cnf)
    assert res_base.is_sat is True


def test_assumptions_self_contradiction() -> None:
    """Contradicting assumptions [x, -x] immediately return UNSAT."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1, 2),), num_primary_vars=2)
    result = solver.solve(cnf, assumptions=[1, -1])
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks >= 1


def test_edge_cases_empty_formula_and_tautologies() -> None:
    """Empty formula is trivially SAT, tautologies are pruned cleanly."""
    solver = DPLLSolver()
    # Empty formula with 3 variables
    cnf_empty = CNFFormula(clauses=(), num_primary_vars=3)
    res_empty = solver.solve(cnf_empty)
    assert res_empty.is_sat is True
    assert res_empty.model is not None
    assert len(res_empty.model) == 3

    # Formula with only tautologies (1 or -1)
    cnf_taut = CNFFormula(clauses=((1, -1), (2, -2, 3)), num_primary_vars=3)
    res_taut = solver.solve(cnf_taut)
    assert res_taut.is_sat is True


def test_zero_variable_formula() -> None:
    """Formula with 0 variables returns SAT with empty model dictionary."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=(), num_primary_vars=0)
    result = solver.solve(cnf)
    assert result.is_sat is True
    assert result.model == {}


def test_literal_zero_in_clauses_raises() -> None:
    """Literal 0 in clauses must raise ValueError."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1, 0), (-1,)), num_primary_vars=1)
    with pytest.raises(ValueError, match="Literal 0 is invalid"):
        solver.solve(cnf)


def test_literal_zero_in_assumptions_raises() -> None:
    """Literal 0 in assumptions must raise ValueError."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1,),), num_primary_vars=1)
    with pytest.raises(ValueError, match="Literal 0 is invalid"):
        solver.solve(cnf, assumptions=[0])


def test_dpll_config_invalid_heuristic_raises() -> None:
    """DPLLConfig with invalid heuristic name must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid heuristic"):
        DPLLConfig(heuristic="invalid_heuristic")  # type: ignore[arg-type]
