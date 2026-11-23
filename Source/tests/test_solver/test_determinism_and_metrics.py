"""Determinism and metrics tests for DPLL SAT Solver.

Verifies:
1. Running solve() multiple times produces strictly identical decisions, propagations, backtracks.
2. Metrics obey sound mathematical properties (non-negative, backtracks >= 0).
"""

from __future__ import annotations

from core.contracts.models import CNFFormula
from solver.dpll_solver import DPLLSolver
from solver.heuristics import DPLLConfig


def test_solver_determinism_across_multiple_runs() -> None:
    """Ensure DPLL gives strictly deterministic decision, propagation, and backtrack counts."""
    clauses = (
        (1, 2, 3),
        (-1, 2, -3),
        (1, -2, 3),
        (-1, -2, -3),
        (2, 3, 4),
        (-2, -4),
        (1, -4),
    )
    cnf = CNFFormula(clauses=clauses, num_primary_vars=4)

    for h in ("lexicographic", "moms", "jw"):
        solver = DPLLSolver(DPLLConfig(heuristic=h))

        run1 = solver.solve(cnf)
        run2 = solver.solve(cnf)
        run3 = solver.solve(cnf)

        assert run1.is_sat == run2.is_sat == run3.is_sat
        assert run1.metrics.decisions == run2.metrics.decisions == run3.metrics.decisions
        assert run1.metrics.propagations == run2.metrics.propagations == run3.metrics.propagations
        assert run1.metrics.backtracks == run2.metrics.backtracks == run3.metrics.backtracks
        assert run1.model == run2.model == run3.model


def test_metrics_on_unsat_formula() -> None:
    """Ensure conflict and backtracks are properly counted for unsatisfiable formulas."""
    # Complete contradiction over 3 variables
    clauses = (
        (1, 2, 3),
        (1, 2, -3),
        (1, -2, 3),
        (1, -2, -3),
        (-1, 2, 3),
        (-1, 2, -3),
        (-1, -2, 3),
        (-1, -2, -3),
    )
    cnf = CNFFormula(clauses=clauses, num_primary_vars=3)
    solver = DPLLSolver()
    result = solver.solve(cnf)

    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.decisions > 0
    assert result.metrics.backtracks > 0
    assert result.metrics.runtime_ms >= 0.0
