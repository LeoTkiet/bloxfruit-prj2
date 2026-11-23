"""Core DPLL SAT Solver implementation for Griductive Solver (TV3).

This module implements a pure Python SAT solver following the classic
Davis-Putnam-Logemann-Loveland (DPLL) procedure:
1. Unit propagation (iterative simplification via unit clause rule).
2. Conflict detection (early stopping upon detecting empty clauses).
3. Deterministic variable selection (lexicographic, MOMs, Jeroslow-Wang).
4. Recursive branching and backtracking with clean trail-based undo.
5. Standardized output: `SATResult` with complete model or `None`.
6. Exact performance metrics recording: decisions, propagations, backtracks, runtime_ms.

In addition, it provides:
- Safe, non-destructive assumptions handling.
- Efficient preprocessed clause caching across repeated queries on identical formulas.
- Configurable branching heuristics and pure-literal elimination.
- Full compliance with `core.contracts.interfaces.ISATSolver`.
"""

from __future__ import annotations

import sys
import time
from typing import Optional, Sequence

from core.contracts.models import CNFFormula, SATMetrics, SATResult
from solver.heuristics import (
    DPLLConfig,
    find_pure_literals,
    select_branching_variable,
)


class DPLLSolver:
    """Deterministic DPLL SAT solver complying with `ISATSolver` protocol."""

    def __init__(self, config: Optional[DPLLConfig] = None) -> None:
        """Initialize DPLLSolver with optional heuristic configuration.

        Args:
            config: DPLLConfig instance controlling heuristic, pure literal, etc.
                    Defaults to lexicographic heuristic with pure literals disabled.
        """
        self.config: DPLLConfig = config or DPLLConfig()

        # Cache preprocessed clauses by formula id for repeated queries on same CNF
        self._cleaned_cache: dict[int, tuple[tuple[tuple[int, ...], ...], bool, int]] = {}

        # Internal state reset per solve invocation
        self._clauses: tuple[tuple[int, ...], ...] = ()
        self._num_vars: int = 0
        self._assignment: list[Optional[bool]] = []
        self._unassigned_vars: set[int] = set()
        self._trail: list[int] = []

        # Metrics
        self._decisions: int = 0
        self._propagations: int = 0
        self._backtracks: int = 0

    def solve(
        self,
        cnf: CNFFormula,
        assumptions: Sequence[int] = (),
    ) -> SATResult:
        """Solve a CNF formula with temporary assumptions using DPLL.

        Args:
            cnf: Immutable CNFFormula data model.
            assumptions: Sequence of unit literal assumptions (e.g. [-1, 5]).
                         Treated non-destructively without modifying `cnf`.

        Returns:
            `SATResult` containing `is_sat`, complete `model` (if SAT),
            and `metrics` (decisions, propagations, backtracks, runtime_ms).

        Raises:
            ValueError: If literal 0 is encountered in clauses or assumptions.
        """
        start_time = time.perf_counter()

        # Safely accommodate deep backtracking trees if needed
        if sys.getrecursionlimit() < 10000:
            try:
                sys.setrecursionlimit(10000)
            except Exception:
                pass

        # Validate assumptions and check for literal 0
        seen_assumptions: set[int] = set()
        for lit in assumptions:
            if lit == 0:
                raise ValueError("Literal 0 is invalid in assumptions.")
            if -lit in seen_assumptions:
                # Contradictory assumptions: e.g. [1, -1]
                self._backtracks = 1
                runtime_ms = (time.perf_counter() - start_time) * 1000.0
                return SATResult(
                    is_sat=False,
                    model=None,
                    metrics=SATMetrics(
                        decisions=0,
                        propagations=0,
                        backtracks=1,
                        runtime_ms=runtime_ms,
                    ),
                )
            seen_assumptions.add(lit)

        # Preprocess / retrieve cached cleaned clauses
        cnf_key = id(cnf.clauses)
        cached = self._cleaned_cache.get(cnf_key)

        if cached is not None:
            cleaned_clauses, has_initial_empty_clause, max_clause_var = cached
        else:
            cleaned_list: list[tuple[int, ...]] = []
            has_initial_empty_clause = False
            max_clause_var = 0

            for raw_clause in cnf.clauses:
                if len(raw_clause) == 0:
                    has_initial_empty_clause = True
                    break

                for lit in raw_clause:
                    if lit == 0:
                        raise ValueError("Literal 0 is invalid in CNF clauses.")
                    abs_l = abs(lit)
                    if abs_l > max_clause_var:
                        max_clause_var = abs_l

                # Remove duplicate literals while preserving order
                unique_lits = tuple(dict.fromkeys(raw_clause))
                lit_set = set(unique_lits)
                # Tautology elimination: clause contains both lit and -lit
                if any(-l in lit_set for l in unique_lits):
                    continue
                cleaned_list.append(unique_lits)

            cleaned_clauses = tuple(cleaned_list)
            # Store in cache (keep cache size bounded)
            if len(self._cleaned_cache) > 256:
                self._cleaned_cache.clear()
            self._cleaned_cache[cnf_key] = (cleaned_clauses, has_initial_empty_clause, max_clause_var)

        # Determine variable domain
        max_var = max(cnf.num_vars, max_clause_var)
        for lit in assumptions:
            abs_l = abs(lit)
            if abs_l > max_var:
                max_var = abs_l

        self._num_vars = max_var
        self._clauses = cleaned_clauses

        # Reset counters
        self._decisions = 0
        self._propagations = 0
        self._backtracks = 0

        # Fast path 1: Initial empty clause -> immediate UNSAT
        if has_initial_empty_clause:
            self._backtracks = 1
            runtime_ms = (time.perf_counter() - start_time) * 1000.0
            return SATResult(
                is_sat=False,
                model=None,
                metrics=SATMetrics(
                    decisions=0,
                    propagations=0,
                    backtracks=1,
                    runtime_ms=runtime_ms,
                ),
            )

        # Fast path 2: Zero-variable formula with no clauses -> trivially SAT with empty model
        if self._num_vars == 0:
            runtime_ms = (time.perf_counter() - start_time) * 1000.0
            return SATResult(
                is_sat=True,
                model={},
                metrics=SATMetrics(
                    decisions=0,
                    propagations=0,
                    backtracks=0,
                    runtime_ms=runtime_ms,
                ),
            )

        # Initialize partial assignment: [None, assign_1, ..., assign_num_vars]
        self._assignment = [None] * (self._num_vars + 1)
        self._unassigned_vars = set(range(1, self._num_vars + 1))
        self._trail = []

        # Apply assumptions at decision level 0
        for lit in assumptions:
            var = abs(lit)
            val = lit > 0
            if self._assignment[var] is None:
                self._assign(var, val)

        # Run DPLL recursive procedure
        is_sat = self._dpll()

        runtime_ms = (time.perf_counter() - start_time) * 1000.0

        if is_sat:
            # Build complete assignment: unassigned variables default to False
            complete_model: dict[int, bool] = {
                v: (self._assignment[v] if self._assignment[v] is not None else False)
                for v in range(1, self._num_vars + 1)
            }
            return SATResult(
                is_sat=True,
                model=complete_model,
                metrics=SATMetrics(
                    decisions=self._decisions,
                    propagations=self._propagations,
                    backtracks=self._backtracks,
                    runtime_ms=runtime_ms,
                ),
            )
        else:
            return SATResult(
                is_sat=False,
                model=None,
                metrics=SATMetrics(
                    decisions=self._decisions,
                    propagations=self._propagations,
                    backtracks=self._backtracks,
                    runtime_ms=runtime_ms,
                ),
            )

    # -----------------------------------------------------------------------
    # Internal DPLL helpers
    # -----------------------------------------------------------------------

    def _assign(self, var: int, val: bool) -> None:
        """Assign boolean value to variable, record on trail, and update unassigned set."""
        self._assignment[var] = val
        self._unassigned_vars.discard(var)
        self._trail.append(var)

    def _undo_to(self, mark: int) -> None:
        """Undo all variable assignments made after trail index `mark`."""
        while len(self._trail) > mark:
            var = self._trail.pop()
            self._assignment[var] = None
            self._unassigned_vars.add(var)

    def _unit_propagate(self) -> bool:
        """Propagate unit clauses in passes until fixpoint or conflict.

        Scans all clauses per round rather than breaking immediately, reducing
        outer scans from O(#units * |F|) to typically 1-2 passes * |F|.

        Returns:
            True if fixpoint is reached without conflicts.
            False if a conflict (empty clause) is detected.
        """
        while True:
            unit_found = False
            for clause in self._clauses:
                sat = False
                unassigned_count = 0
                last_unassigned_lit = 0

                for lit in clause:
                    v = abs(lit)
                    val = self._assignment[v]
                    if val is not None:
                        if val == (lit > 0):
                            sat = True
                            break
                    else:
                        unassigned_count += 1
                        last_unassigned_lit = lit

                if sat:
                    continue

                if unassigned_count == 0:
                    # Conflict: all literals in clause are False under current assignment
                    self._backtracks += 1
                    return False

                if unassigned_count == 1:
                    # Unit clause
                    v = abs(last_unassigned_lit)
                    if self._assignment[v] is None:
                        self._assign(v, last_unassigned_lit > 0)
                        self._propagations += 1
                        unit_found = True

            if not unit_found:
                break

        return True

    def _get_unresolved_clauses(self) -> list[tuple[int, ...]]:
        """Return all clauses not yet satisfied under current assignment."""
        unresolved: list[tuple[int, ...]] = []
        for clause in self._clauses:
            sat = False
            for lit in clause:
                val = self._assignment[abs(lit)]
                if val is not None and val == (lit > 0):
                    sat = True
                    break
            if not sat:
                unresolved.append(clause)
        return unresolved

    def _dpll(self) -> bool:
        """Recursive DPLL search procedure.

        Returns:
            True if current partial assignment can be extended to satisfy all clauses.
            False if unsatisfiable from current state.
        """
        trail_mark = len(self._trail)

        # 1. Unit Propagation
        if not self._unit_propagate():
            self._undo_to(trail_mark)
            return False

        # 2. Pure-Literal Elimination (if enabled)
        unresolved = self._get_unresolved_clauses()
        if not unresolved:
            return True

        if self.config.enable_pure_literal and self._unassigned_vars:
            pure_lits = find_pure_literals(list(self._unassigned_vars), unresolved, self._assignment)
            if pure_lits:
                for lit in pure_lits:
                    v = abs(lit)
                    if self._assignment[v] is None:
                        self._assign(v, lit > 0)
                unresolved = self._get_unresolved_clauses()
                if not unresolved:
                    return True

        if not self._unassigned_vars:
            return True

        # 3. Deterministic Variable Selection
        var, first_polarity = select_branching_variable(
            list(self._unassigned_vars),
            unresolved,
            self._assignment,
            self.config,
        )

        self._decisions += 1

        # 4. Recursive Branching & Backtracking
        # Try Branch 1: var = first_polarity
        branch_mark = len(self._trail)
        self._assign(var, first_polarity)
        if self._dpll():
            return True

        # Backtrack Branch 1
        self._undo_to(branch_mark)

        # Try Branch 2: var = not first_polarity
        self._assign(var, not first_polarity)
        if self._dpll():
            return True

        # Backtrack Branch 2
        self._undo_to(branch_mark)

        # Both branches failed: undo all assignments made at this level and return False
        self._undo_to(trail_mark)
        return False
