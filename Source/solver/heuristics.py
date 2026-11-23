"""Branching heuristics, pure literal elimination, and DPLL configuration.

This module provides deterministic variable selection heuristics for DPLL SAT solving:
- `DPLLConfig`: configuration dataclass controlling heuristics, pure literal elimination,
  and polarity preferences.
- `lexicographic_heuristic`: pick the smallest unassigned variable index.
- `moms_heuristic`: Maximum Occurrences in clauses of Minimum Size (MOM's rule).
- `jw_heuristic`: Two-sided Jeroslow-Wang heuristic with exponential clause weighting.
- `find_pure_literals`: detect literals occurring with only one polarity in unresolved clauses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

BranchingHeuristic = Literal["lexicographic", "moms", "jw"]


@dataclass(frozen=True)
class DPLLConfig:
    """Configuration parameters for DPLL SAT Solver.

    Attributes:
        heuristic: Variable selection rule ('lexicographic', 'moms', 'jw').
        enable_pure_literal: If True, execute Pure-Literal Elimination in DPLL loop.
        default_polarity: Initial boolean truth assignment when branching (True or False).
    """

    heuristic: BranchingHeuristic = "lexicographic"
    enable_pure_literal: bool = False
    default_polarity: bool = True

    def __post_init__(self) -> None:
        valid_heuristics = ("lexicographic", "moms", "jw")
        if self.heuristic not in valid_heuristics:
            raise ValueError(
                f"Invalid heuristic: {self.heuristic!r}. Expected one of {valid_heuristics}."
            )


def select_branching_variable(
    unassigned_vars: Sequence[int],
    unresolved_clauses: Sequence[Sequence[int]],
    assignment: Sequence[bool | None],
    config: DPLLConfig,
) -> tuple[int, bool]:
    """Select the next variable and branch polarity deterministically according to config.

    Args:
        unassigned_vars: Sequence of currently unassigned variable indices (1-based).
        unresolved_clauses: Clauses that are not yet satisfied under `assignment`.
        assignment: Current partial assignment (index 1..N, None if unassigned).
        config: DPLLConfig specifying heuristic and default polarity.

    Returns:
        tuple (var, first_polarity) indicating which variable to branch on and
        which boolean value to try first.
    """
    if not unassigned_vars:
        raise ValueError("Cannot select branching variable from empty unassigned list.")

    if config.heuristic == "lexicographic":
        return lexicographic_heuristic(unassigned_vars, config.default_polarity)
    elif config.heuristic == "moms":
        return moms_heuristic(unassigned_vars, unresolved_clauses, assignment, config.default_polarity)
    elif config.heuristic == "jw":
        return jw_heuristic(unassigned_vars, unresolved_clauses, assignment, config.default_polarity)
    else:
        return lexicographic_heuristic(unassigned_vars, config.default_polarity)


def lexicographic_heuristic(
    unassigned_vars: Sequence[int],
    default_polarity: bool = True,
) -> tuple[int, bool]:
    """Pick the smallest variable index deterministically.

    Args:
        unassigned_vars: List/set of unassigned variables.
        default_polarity: Value to branch first.

    Returns:
        tuple (min_var, default_polarity).
    """
    var = min(unassigned_vars)
    return var, default_polarity


def moms_heuristic(
    unassigned_vars: Sequence[int],
    unresolved_clauses: Sequence[Sequence[int]],
    assignment: Sequence[bool | None],
    default_polarity: bool = True,
) -> tuple[int, bool]:
    """Maximum Occurrences in clauses of Minimum Size (MOM's heuristic).

    Identifies the minimum active size `k` among unsatisfied clauses, then scores
    unassigned variables based on occurrences in clauses of size `k`.
    Score function: (pos[v] + neg[v]) * 2^k + pos[v] * neg[v].
    Ties broken deterministically by smallest variable index.
    """
    # Filter active literals for each unresolved clause
    clause_active_lits: list[list[int]] = []
    min_len = 1000000

    for clause in unresolved_clauses:
        active = [lit for lit in clause if assignment[abs(lit)] is None]
        if active:
            clause_active_lits.append(active)
            if len(active) < min_len:
                min_len = len(active)

    if not clause_active_lits:
        return min(unassigned_vars), default_polarity

    # Count occurrences in clauses of minimum size
    pos_counts: dict[int, int] = {v: 0 for v in unassigned_vars}
    neg_counts: dict[int, int] = {v: 0 for v in unassigned_vars}

    for active in clause_active_lits:
        if len(active) == min_len:
            for lit in active:
                v = abs(lit)
                if v in pos_counts:
                    if lit > 0:
                        pos_counts[v] += 1
                    else:
                        neg_counts[v] += 1

    best_score = -1
    best_var = min(unassigned_vars)
    best_polarity = default_polarity
    weight = 1 << min(min_len, 20)

    # Sort variables deterministically by index
    for v in sorted(unassigned_vars):
        p = pos_counts[v]
        n = neg_counts[v]
        score = (p + n) * weight + (p * n)
        if score > best_score:
            best_score = score
            best_var = v
            # Branch first on polarity with more occurrences
            best_polarity = (p >= n) if (p + n > 0) else default_polarity

    return best_var, best_polarity


def jw_heuristic(
    unassigned_vars: Sequence[int],
    unresolved_clauses: Sequence[Sequence[int]],
    assignment: Sequence[bool | None],
    default_polarity: bool = True,
) -> tuple[int, bool]:
    """Two-sided Jeroslow-Wang heuristic with exponential clause weighting.

    Assigns weight 2^(-|clause|) to each active literal in unsatisfied clauses.
    For variable v, score = J(v) + J(-v).
    Ties broken deterministically by smallest variable index.
    Branches first on the literal with higher J value.
    """
    j_pos: dict[int, float] = {v: 0.0 for v in unassigned_vars}
    j_neg: dict[int, float] = {v: 0.0 for v in unassigned_vars}

    # Powers of 2 cache for small clause lengths
    pow2: dict[int, float] = {k: 2.0 ** (-k) for k in range(1, 100)}

    for clause in unresolved_clauses:
        active = [lit for lit in clause if assignment[abs(lit)] is None]
        k = len(active)
        if k == 0:
            continue
        w = pow2.get(k, 2.0 ** (-k))
        for lit in active:
            v = abs(lit)
            if v in j_pos:
                if lit > 0:
                    j_pos[v] += w
                else:
                    j_neg[v] += w

    best_score = -1.0
    best_var = min(unassigned_vars)
    best_polarity = default_polarity

    for v in sorted(unassigned_vars):
        score = j_pos[v] + j_neg[v]
        if score > best_score:
            best_score = score
            best_var = v
            best_polarity = (j_pos[v] >= j_neg[v]) if score > 0 else default_polarity

    return best_var, best_polarity


def find_pure_literals(
    unassigned_vars: Sequence[int],
    unresolved_clauses: Sequence[Sequence[int]],
    assignment: Sequence[bool | None],
) -> list[int]:
    """Find all pure literals among currently unresolved clauses.

    A literal is pure if it appears with only one polarity across all unresolved clauses.
    Returns:
        List of pure literals sorted by variable index (e.g. [+3, -7]).
    """
    has_pos: dict[int, bool] = {v: False for v in unassigned_vars}
    has_neg: dict[int, bool] = {v: False for v in unassigned_vars}

    for clause in unresolved_clauses:
        for lit in clause:
            v = abs(lit)
            if assignment[v] is None:
                if lit > 0:
                    has_pos[v] = True
                else:
                    has_neg[v] = True

    pure_literals: list[int] = []
    for v in sorted(unassigned_vars):
        p = has_pos[v]
        n = has_neg[v]
        if p and not n:
            pure_literals.append(v)
        elif n and not p:
            pure_literals.append(-v)

    return pure_literals
