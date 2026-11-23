"""Brute-force SAT Oracle cross-validation tests for DPLLSolver.

Runs an independent brute-force truth table solver on formulas with <= 12 variables
and verifies 100% agreement with DPLLSolver (both SAT and UNSAT).
For SAT instances, also verifies that the model returned by DPLL satisfies every clause.
"""

from __future__ import annotations

import itertools
import random
from typing import Mapping, Optional, Sequence

import pytest
from core.contracts.models import CNFFormula
from solver.dpll_solver import DPLLSolver
from solver.heuristics import DPLLConfig


def brute_force_sat(
    clauses: Sequence[Sequence[int]],
    num_vars: int,
    assumptions: Sequence[int] = (),
) -> tuple[bool, Optional[dict[int, bool]]]:
    """Exhaustive truth table search for satisfiable assignment."""
    assump_map: dict[int, bool] = {abs(l): (l > 0) for l in assumptions}

    for bits in itertools.product([False, True], repeat=num_vars):
        assign = {v: bits[v - 1] for v in range(1, num_vars + 1)}

        # Check assumptions
        if any(assign[v] != val for v, val in assump_map.items()):
            continue

        # Check all clauses
        satisfied_all = True
        for clause in clauses:
            clause_sat = any(
                (lit > 0 and assign[abs(lit)]) or (lit < 0 and not assign[abs(lit)])
                for lit in clause
            )
            if not clause_sat:
                satisfied_all = False
                break

        if satisfied_all:
            return True, assign

    return False, None


def verify_model_satisfies_cnf(
    clauses: Sequence[Sequence[int]],
    model: Mapping[int, bool],
    assumptions: Sequence[int] = (),
) -> bool:
    """Verify that every literal in assumptions and every clause is satisfied by model."""
    for lit in assumptions:
        v = abs(lit)
        if model.get(v) != (lit > 0):
            return False

    for clause in clauses:
        if not clause:
            return False
        sat = False
        for lit in clause:
            v = abs(lit)
            if (lit > 0 and model.get(v, False)) or (lit < 0 and not model.get(v, False)):
                sat = True
                break
        if not sat:
            return False
    return True


@pytest.mark.parametrize("seed", [42, 101, 2024, 777, 999])
def test_dpll_vs_brute_force_random_formulas(seed: int) -> None:
    """Test 5 randomly generated 3-SAT instances against brute-force solver."""
    rng = random.Random(seed)
    num_vars = 6
    num_clauses = 18

    clauses: list[tuple[int, ...]] = []
    for _ in range(num_clauses):
        vars_chosen = rng.sample(range(1, num_vars + 1), 3)
        lits = tuple(v if rng.choice([True, False]) else -v for v in vars_chosen)
        clauses.append(lits)

    cnf = CNFFormula(clauses=tuple(clauses), num_primary_vars=num_vars)

    bf_sat, bf_model = brute_force_sat(clauses, num_vars)

    # Test lexicographic, moms, and jw configurations
    for h in ("lexicographic", "moms", "jw"):
        solver = DPLLSolver(DPLLConfig(heuristic=h))
        res = solver.solve(cnf)

        assert res.is_sat == bf_sat, f"Disagreement on seed={seed}, heuristic={h}"
        if res.is_sat:
            assert res.model is not None
            assert verify_model_satisfies_cnf(clauses, res.model)


def test_dpll_vs_brute_force_with_assumptions() -> None:
    """Test formulas with various positive and negative assumptions against brute force."""
    num_vars = 5
    clauses = (
        (1, 2, -3),
        (-1, 3, 4),
        (-2, -4, 5),
        (-3, -5),
    )
    cnf = CNFFormula(clauses=clauses, num_primary_vars=num_vars)
    solver = DPLLSolver()

    test_assumptions_list = [
        [],
        [1],
        [-1],
        [1, 2],
        [-1, -2],
        [3, -4, 5],
        [1, -3, 5],
    ]

    for assumptions in test_assumptions_list:
        bf_sat, _ = brute_force_sat(clauses, num_vars, assumptions)
        res = solver.solve(cnf, assumptions=assumptions)

        assert res.is_sat == bf_sat, f"Disagreement on assumptions={assumptions}"
        if res.is_sat:
            assert res.model is not None
            assert verify_model_satisfies_cnf(clauses, res.model, assumptions)
