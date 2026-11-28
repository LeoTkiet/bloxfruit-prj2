"""Auto-solve terminal outcomes and outcome derivation helpers."""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from core.contracts.models import DeductionStep, PublicState, VerdictCode


class AutoSolveOutcome(str, Enum):
    """Terminal state of `DeductiveLogicAgent.run_auto_solve`."""

    SOLVED = "SOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    INCONSISTENT = "INCONSISTENT"


def outcome_of(
    steps: Sequence[DeductionStep],
    final_state: PublicState,
) -> AutoSolveOutcome:
    """Derive `AutoSolveOutcome` from the deduction trace and final public state."""
    if steps:
        last = steps[-1]
        # CONTRADICTED on a verdict the agent just proved forced means the agent's
        # KB_t and the engine disagree: an inconsistency, not an ambiguous board.
        if last.verdict_code in (VerdictCode.INCONSISTENT, VerdictCode.CONTRADICTED):
            return AutoSolveOutcome.INCONSISTENT
        if last.verdict_code == VerdictCode.NOT_PROVABLE:
            return AutoSolveOutcome.AMBIGUOUS

    if final_state.is_solved:
        return AutoSolveOutcome.SOLVED

    return AutoSolveOutcome.AMBIGUOUS
