"""Contract compliance tests for TV3 DPLL SAT Solver."""

from __future__ import annotations

from core.contracts.interfaces import ISATSolver
from core.contracts.models import CNFFormula, SATMetrics, SATResult
from solver.dpll_solver import DPLLSolver


def test_isatsolver_protocol_conformance() -> None:
    """Verify DPLLSolver conforms to ISATSolver runtime checkable protocol."""
    solver = DPLLSolver()
    assert isinstance(solver, ISATSolver), "DPLLSolver must implement ISATSolver protocol"


def test_solve_returns_sat_result_with_proper_structure() -> None:
    """Verify solve() returns a properly populated SATResult with frozen model and metrics."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1, 2), (-1,)), num_primary_vars=2)
    result = solver.solve(cnf)

    assert isinstance(result, SATResult)
    assert result.is_sat is True
    assert result.model is not None
    assert result.model[1] is False
    assert result.model[2] is True

    # Check metrics
    assert isinstance(result.metrics, SATMetrics)
    assert result.metrics.decisions >= 0
    assert result.metrics.propagations >= 1  # [-1] unit propagation
    assert result.metrics.backtracks >= 0
    assert result.metrics.runtime_ms >= 0.0


def test_unsat_result_has_none_model() -> None:
    """Verify an unsatisfiable formula returns is_sat=False and model=None."""
    solver = DPLLSolver()
    cnf = CNFFormula(clauses=((1,), (-1,)), num_primary_vars=1)
    result = solver.solve(cnf)

    assert isinstance(result, SATResult)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks >= 1
