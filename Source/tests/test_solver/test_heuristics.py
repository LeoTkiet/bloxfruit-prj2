"""Tests for branching heuristics and pure-literal elimination."""

from __future__ import annotations

from core.contracts.models import CNFFormula
from solver.dpll_solver import DPLLSolver
from solver.heuristics import (
    DPLLConfig,
    find_pure_literals,
    jw_heuristic,
    lexicographic_heuristic,
    moms_heuristic,
)


def test_pure_literal_detection() -> None:
    """Test pure literal detection in unresolved clauses."""
    # Clauses: (1, 2), (-1, 2), (3, -4)
    # Variable 2 is pure positive (only +2 appears)
    # Variable 3 is pure positive (+3)
    # Variable 4 is pure negative (-4)
    unassigned = [1, 2, 3, 4]
    clauses = [[1, 2], [-1, 2], [3, -4]]
    assign = [None] * 5

    pure = find_pure_literals(unassigned, clauses, assign)
    assert 2 in pure
    assert 3 in pure
    assert -4 in pure
    assert 1 not in pure and -1 not in pure


def test_heuristics_selection_tie_breaking() -> None:
    """Verify tie-breaking is deterministic (smallest variable index)."""
    unassigned = [4, 2, 3]
    var, pol = lexicographic_heuristic(unassigned, default_polarity=True)
    assert var == 2
    assert pol is True


def test_polarity_tie_breaking_obeys_default_polarity() -> None:
    """When positive and negative occurrences are equal (p == n > 0), obey default_polarity."""
    # Clauses where variable 1 has 1 positive and 1 negative occurrence of equal clause length
    unassigned = [1]
    clauses = [[1, 2], [-1, 3]]
    assign = [None] * 4

    # MOMs
    _, pol_true = moms_heuristic(unassigned, clauses, assign, default_polarity=True)
    assert pol_true is True

    _, pol_false = moms_heuristic(unassigned, clauses, assign, default_polarity=False)
    assert pol_false is False

    # JW
    _, jw_true = jw_heuristic(unassigned, clauses, assign, default_polarity=True)
    assert jw_true is True

    _, jw_false = jw_heuristic(unassigned, clauses, assign, default_polarity=False)
    assert jw_false is False


def test_solve_with_pure_literal_elimination() -> None:
    """Verify solver with pure-literal elimination solves correctly."""
    clauses = (
        (1, 2),
        (1, -2),
        (3, 4),
        (-3, 4),
    )
    cnf = CNFFormula(clauses=clauses, num_primary_vars=4)

    solver_pure = DPLLSolver(DPLLConfig(enable_pure_literal=True))
    result = solver_pure.solve(cnf)

    assert result.is_sat is True
    assert result.model is not None
    # 1 is pure positive, 4 is pure positive
    assert result.model[1] is True
    assert result.model[4] is True


def test_all_heuristics_solve_satisfiable_formula() -> None:
    """Verify all 3 heuristics (lexicographic, moms, jw) solve a satisfiable instance."""
    clauses = (
        (1, 2, -3),
        (-1, -2, 3),
        (2, 3),
        (-2, -3),
    )
    cnf = CNFFormula(clauses=clauses, num_primary_vars=3)

    for h in ("lexicographic", "moms", "jw"):
        solver = DPLLSolver(DPLLConfig(heuristic=h))
        res = solver.solve(cnf)
        assert res.is_sat is True
        assert res.model is not None
        # Verify model satisfies all clauses
        for clause in clauses:
            assert any(
                (lit > 0 and res.model[abs(lit)]) or (lit < 0 and not res.model[abs(lit)])
                for lit in clause
            )
