"""Temporary deterministic SAT solver used by TV4 until TV3's `solver.DPLLSolver` is merged.

It implements `ISATSolver` with a minimal DPLL (unit propagation + lexicographic
branching, True first) so `agent/` and `experiments/` can be tested on `dev`
without depending on `solver/`. Its metrics are NOT comparable to TV3's solver:
never use stub figures in the final report.
"""

from __future__ import annotations

import time
from typing import Optional, Sequence

from core.contracts.models import CNFFormula, SATMetrics, SATResult


class StubDPLLSolver:
    """Small, deterministic DPLL solver satisfying `ISATSolver` (TV4 test double)."""

    def solve(self, cnf: CNFFormula, assumptions: Sequence[int] = ()) -> SATResult:
        start = time.perf_counter()
        counters = {"decisions": 0, "propagations": 0, "backtracks": 0}
        num_vars = cnf.num_primary_vars + cnf.num_aux_vars
        for clause in cnf.clauses:
            for lit in clause:
                num_vars = max(num_vars, abs(lit))
        for lit in assumptions:
            num_vars = max(num_vars, abs(lit))

        assignment: dict[int, bool] = {}
        model: Optional[dict[int, bool]] = None
        if self._assume(assignment, assumptions):
            model = self._search(cnf.clauses, assignment, counters)

        metrics = SATMetrics(
            decisions=counters["decisions"],
            propagations=counters["propagations"],
            backtracks=counters["backtracks"],
            runtime_ms=(time.perf_counter() - start) * 1000.0,
        )
        if model is None:
            return SATResult(is_sat=False, model=None, metrics=metrics)
        complete = {v: model.get(v, False) for v in range(1, num_vars + 1)}
        return SATResult(is_sat=True, model=complete, metrics=metrics)

    @staticmethod
    def _assume(assignment: dict[int, bool], assumptions: Sequence[int]) -> bool:
        for lit in assumptions:
            if lit == 0:
                raise ValueError("Literal 0 is not a valid assumption")
            var, value = abs(lit), lit > 0
            if assignment.get(var, value) != value:
                return False
            assignment[var] = value
        return True

    def _search(
        self,
        clauses: Sequence[Sequence[int]],
        assignment: dict[int, bool],
        counters: dict[str, int],
    ) -> Optional[dict[int, bool]]:
        if not self._propagate(clauses, assignment, counters):
            return None
        branch_var = self._pick_branch_var(clauses, assignment)
        if branch_var is None:
            return assignment
        counters["decisions"] += 1
        for value in (True, False):
            trial = dict(assignment)
            trial[branch_var] = value
            result = self._search(clauses, trial, counters)
            if result is not None:
                return result
            counters["backtracks"] += 1
        return None

    @staticmethod
    def _propagate(
        clauses: Sequence[Sequence[int]],
        assignment: dict[int, bool],
        counters: dict[str, int],
    ) -> bool:
        """Apply unit propagation in place; return False on conflict."""
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                unassigned: list[int] = []
                satisfied = False
                for lit in clause:
                    value = assignment.get(abs(lit))
                    if value is None:
                        unassigned.append(lit)
                    elif value == (lit > 0):
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unassigned:
                    return False
                if len(unassigned) == 1:
                    lit = unassigned[0]
                    assignment[abs(lit)] = lit > 0
                    counters["propagations"] += 1
                    changed = True
        return True

    @staticmethod
    def _pick_branch_var(
        clauses: Sequence[Sequence[int]], assignment: dict[int, bool]
    ) -> Optional[int]:
        """Smallest unassigned variable occurring in a not-yet-satisfied clause."""
        best: Optional[int] = None
        for clause in clauses:
            if any(assignment.get(abs(l)) == (l > 0) for l in clause):
                continue
            for lit in clause:
                var = abs(lit)
                if var not in assignment and (best is None or var < best):
                    best = var
        return best
