"""Direct semantic evaluator used as ground-truth oracle (owned by TV2).

Implements `IDirectEvaluator`. Given a complete boolean assignment of the grid,
each clue is evaluated directly from its specification — the CNF encoder, the
DPLL solver and any hidden puzzle data are never consulted.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CNFFormula,
    CompareOp,
    ParityKind,
    Status,
    all_cell_ids,
)
from logic.region_resolver import resolve_region_cells

__all__ = ["DirectSemanticEvaluator", "evaluate_cnf_clauses", "evaluate_formula"]


def _validate_assignment(
    assignment: Mapping[CellID, bool], grid_size: int
) -> None:
    expected = set(all_cell_ids(grid_size))
    provided = set(assignment)
    if provided != expected:
        missing = sorted(expected - provided)
        extra = sorted(provided - expected)
        raise ValueError(
            "Assignment must contain exactly one boolean per grid cell "
            f"(missing={missing}, extra={extra})"
        )
    if not all(isinstance(value, bool) for value in assignment.values()):
        raise ValueError("Assignment values must be booleans (True = Criminal)")


def evaluate_cnf_clauses(
    clauses: Iterable[Sequence[int]],
    assignment: Mapping[int, bool],
) -> bool:
    """Evaluate a CNF formula directly under a variable->truth mapping.

    This is a tiny, side-effect-free clause checker used for cross-verification;
    it is not a SAT solver and does not try to extend partial assignments.
    """
    for clause in clauses:
        satisfied = False
        for literal in clause:
            if literal == 0:
                raise ValueError("CNF literals must be non-zero integers")
            var = abs(literal)
            if var not in assignment:
                raise ValueError(f"Variable {var} is missing from the assignment")
            value = assignment[var]
            if (literal > 0 and value) or (literal < 0 and not value):
                satisfied = True
                break
        if not satisfied:
            return False
    return True


def evaluate_formula(
    formula: CNFFormula,
    assignment: Mapping[int, bool],
) -> bool:
    """Evaluate a complete `CNFFormula` under a complete variable assignment."""
    expected = set(range(1, formula.num_vars + 1))
    if set(assignment) != expected:
        raise ValueError(
            f"Assignment must cover variables 1..{formula.num_vars} exactly"
        )
    return evaluate_cnf_clauses(formula.clauses, assignment)


class DirectSemanticEvaluator:
    """Evaluate all clue templates directly from their structured meaning."""

    def evaluate_clue_direct(
        self,
        clue: Clue,
        assignment: Mapping[CellID, bool],
        grid_size: int,
    ) -> bool:
        """Return True iff `clue` holds under the complete grid `assignment`."""
        _validate_assignment(assignment, grid_size)
        clue_type = clue.clue_type
        context = repr(clue.clue_id)

        if clue_type == ClueType.FACT:
            if clue.target is None or clue.target_status not in (
                Status.CRIMINAL,
                Status.INNOCENT,
            ):
                raise ValueError(f"Invalid FACT clue {context}")
            expected = clue.target_status == Status.CRIMINAL
            return assignment[clue.target] is expected

        if clue_type in (ClueType.SAME, ClueType.DIFFERENT):
            if len(clue.targets) != 2:
                raise ValueError(
                    f"{clue_type.value} clue {context} requires 2 targets"
                )
            first, second = clue.targets
            same = assignment[first] is assignment[second]
            return same if clue_type == ClueType.SAME else not same

        if clue_type in (
            ClueType.EXACTLY,
            ClueType.AT_LEAST,
            ClueType.AT_MOST,
        ):
            if clue.region is None or clue.count is None:
                raise ValueError(f"Cardinality clue {context} requires region/count")
            cells = resolve_region_cells(clue.region, grid_size)
            count = sum(1 for cell in cells if assignment[cell])
            k = clue.count
            if clue_type == ClueType.EXACTLY:
                return count == k
            if clue_type == ClueType.AT_LEAST:
                return count >= k
            return count <= k

        if clue_type == ClueType.PARITY:
            if clue.region is None or clue.parity not in (
                ParityKind.EVEN,
                ParityKind.ODD,
            ):
                raise ValueError(f"Invalid PARITY clue {context}")
            cells = resolve_region_cells(clue.region, grid_size)
            count = sum(1 for cell in cells if assignment[cell])
            want_odd = clue.parity == ParityKind.ODD
            return bool(count % 2) == want_odd

        if clue_type == ClueType.COMPARE_COUNTS:
            if (
                clue.region is None
                or clue.region_b is None
                or clue.compare_op not in tuple(CompareOp)
            ):
                raise ValueError(f"Invalid COMPARE_COUNTS clue {context}")
            left_cells = resolve_region_cells(clue.region, grid_size)
            right_cells = resolve_region_cells(clue.region_b, grid_size)
            left = sum(1 for cell in left_cells if assignment[cell])
            right = sum(1 for cell in right_cells if assignment[cell])
            op = clue.compare_op
            if op == CompareOp.EQ:
                return left == right
            if op == CompareOp.LT:
                return left < right
            if op == CompareOp.GT:
                return left > right
            if op == CompareOp.LE:
                return left <= right
            return left >= right

        raise ValueError(f"Unsupported clue type: {clue_type!r}")
