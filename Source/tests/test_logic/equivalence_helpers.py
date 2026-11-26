"""Small SAT-existence helper used only by TV2's equivalence tests.

It deliberately does not depend on TV3's solver: given a fixed assignment of
primary variables, it uses unit propagation plus binary branching to decide
whether some extension over auxiliary variables satisfies the CNF.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def _propagate(
    clauses: Iterable[Sequence[int]],
    assignment: dict[int, bool],
) -> list[tuple[int, ...]] | None:
    """Apply unit propagation; return remaining unresolved clauses or None."""
    while True:
        remaining: list[tuple[int, ...]] = []
        unit_var: int | None = None
        unit_value = False

        for clause in clauses:
            unresolved: list[int] = []
            for literal in clause:
                var = abs(literal)
                if var in assignment:
                    truth = assignment[var] if literal > 0 else not assignment[var]
                    if truth:
                        break
                else:
                    unresolved.append(literal)
            else:
                if not unresolved:
                    return None
                if len(unresolved) == 1:
                    unit_var = abs(unresolved[0])
                    unit_value = unresolved[0] > 0
                    break
                remaining.append(tuple(unresolved))

        if unit_var is None:
            return remaining
        assignment[unit_var] = unit_value


def _search(clauses: list[tuple[int, ...]], assignment: dict[int, bool]) -> bool:
    reduced = _propagate(clauses, assignment)
    if reduced is None:
        return False
    if not reduced:
        return True
    variable = abs(reduced[0][0])
    for truth in (True, False):
        extended = dict(assignment)
        extended[variable] = truth
        if _search(reduced, extended):
            return True
    return False


def sat_exists_under(
    clauses: Iterable[Sequence[int]],
    fixed_assignment: Mapping[int, bool],
) -> bool:
    """Return True iff some extension of `fixed_assignment` satisfies `clauses`."""
    return _search(list(clauses), dict(fixed_assignment))
