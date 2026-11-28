"""Tests for the temporary StubDPLLSolver and the solver factory fallback."""

from __future__ import annotations

import itertools
import random

from core.contracts.interfaces import ISATSolver
from core.contracts.models import CNFFormula
from experiments import solver_factory
from experiments.stub_solver import StubDPLLSolver


def _cnf(clauses: list[tuple[int, ...]], n: int) -> CNFFormula:
    return CNFFormula(clauses=tuple(clauses), num_primary_vars=n)


def _brute_force_sat(clauses: list[tuple[int, ...]], n: int, assumptions: tuple[int, ...]) -> bool:
    for bits in itertools.product((False, True), repeat=n):
        val = {i + 1: b for i, b in enumerate(bits)}
        if any(val[abs(a)] != (a > 0) for a in assumptions):
            continue
        if all(any(val[abs(l)] == (l > 0) for l in cl) for cl in clauses):
            return True
    return False


def test_stub_satisfies_protocol() -> None:
    assert isinstance(StubDPLLSolver(), ISATSolver)


def test_sat_returns_complete_satisfying_model() -> None:
    clauses = [(1, 2), (-1, 3), (-3,)]
    res = StubDPLLSolver().solve(_cnf(clauses, 4))
    assert res.is_sat
    assert res.model is not None and set(res.model) == {1, 2, 3, 4}
    assert all(any(res.model[abs(l)] == (l > 0) for l in cl) for cl in clauses)


def test_unsat_and_conflicting_assumptions() -> None:
    solver = StubDPLLSolver()
    assert not solver.solve(_cnf([(1,), (-1,)], 1)).is_sat
    assert not solver.solve(_cnf([(1, 2)], 2), (1, -1)).is_sat
    assert not solver.solve(_cnf([(1, 2)], 2), (-1, -2)).is_sat


def test_matches_brute_force_on_random_3sat() -> None:
    rng = random.Random(2026)
    solver = StubDPLLSolver()
    for _ in range(300):
        n = rng.randint(1, 7)
        clauses = [
            tuple(rng.choice((1, -1)) * rng.randint(1, n) for _ in range(rng.randint(1, 3)))
            for _ in range(rng.randint(1, 12))
        ]
        assumptions = tuple(rng.choice((1, -1)) * rng.randint(1, n) for _ in range(rng.randint(0, 2)))
        res = solver.solve(_cnf(clauses, n), assumptions)
        assert res.is_sat == _brute_force_sat(clauses, n, assumptions)
        if res.is_sat:
            assert res.model is not None
            assert all(res.model[abs(a)] == (a > 0) for a in assumptions)
            assert all(any(res.model[abs(l)] == (l > 0) for l in cl) for cl in clauses)


def test_deterministic_model_and_metrics() -> None:
    cnf = _cnf([(1, 2, 3), (-1, -2), (-2, -3), (2, 4)], 4)
    a, b = StubDPLLSolver().solve(cnf), StubDPLLSolver().solve(cnf)
    assert dict(a.model or {}) == dict(b.model or {})
    assert (a.metrics.decisions, a.metrics.propagations, a.metrics.backtracks) == (
        b.metrics.decisions,
        b.metrics.propagations,
        b.metrics.backtracks,
    )


def test_factory_prefers_real_solver_when_available() -> None:
    solver = solver_factory.make_solver()
    if solver_factory.REAL_SOLVER_AVAILABLE:
        assert not isinstance(solver, StubDPLLSolver)
    else:
        assert isinstance(solver, StubDPLLSolver)
