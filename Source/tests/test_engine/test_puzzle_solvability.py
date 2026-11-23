"""End-to-end verification of TV1's complete puzzle dataset (`Source/puzzles/`).

Mathematically verifies every single puzzle file:
1. Dataset meets minimum quota (4x 3x3, 4x 4x4, 2x 5x5, 2+ extensions, 2+ edge_cases).
2. Every file parses cleanly and passes `validate_puzzle`.
3. Every SOLVABLE puzzle:
   - All clues evaluate to True under the puzzle's hidden solution.
   - Complete clue set has a STRICTLY UNIQUE satisfying assignment equal to the solution.
   - Running `GameEngine` + no-guess entailment solves all N^2 characters with 0 guesses.
4. Every AMBIGUOUS edge case:
   - All clues evaluate to True under the hidden solution.
   - No-guess deduction stops safely with NOT_PROVABLE (never guesses).
5. Every INCONSISTENT edge case:
   - Initial KB_0 is immediately detected as UNSAT (INCONSISTENT).
"""

from pathlib import Path

import pytest

from core.contracts.models import Status, VerdictCode
from engine.game_engine import GameEngine
from engine.puzzle_loader import load_puzzle_definition
from engine.puzzle_validator import validate_puzzle
from tests.test_engine.mock_agent import ExactTestOracleAgent, evaluate_clue_truth

PUZZLES_DIR = Path(__file__).resolve().parents[2] / "puzzles"
ALL_PUZZLE_FILES = sorted(PUZZLES_DIR.rglob("*.json"))


def test_puzzle_dataset_meets_required_quotas() -> None:
    assert len(list((PUZZLES_DIR / "3x3").glob("*.json"))) >= 4
    assert len(list((PUZZLES_DIR / "4x4").glob("*.json"))) >= 4
    assert len(list((PUZZLES_DIR / "5x5").glob("*.json"))) >= 2
    assert len(list((PUZZLES_DIR / "extensions").glob("*.json"))) >= 2
    assert len(list((PUZZLES_DIR / "edge_cases").glob("*.json"))) >= 2
    assert len(ALL_PUZZLE_FILES) >= 14


@pytest.mark.parametrize(
    "puzzle_path",
    ALL_PUZZLE_FILES,
    ids=[p.relative_to(PUZZLES_DIR).as_posix() for p in ALL_PUZZLE_FILES],
)
def test_puzzle_validity_uniqueness_and_no_guess_solvability(puzzle_path: Path) -> None:
    puzzle = load_puzzle_definition(puzzle_path)
    validate_puzzle(puzzle)

    oracle = ExactTestOracleAgent()
    engine = GameEngine(logic_agent=oracle)
    engine.load_puzzle(puzzle_path)

    hidden_bool = {
        ch.cell_id: (ch.hidden_status == Status.CRIMINAL)
        for ch in puzzle.characters
    }
    hidden_status = {ch.cell_id: ch.hidden_status for ch in puzzle.characters}

    if puzzle.expected_status == "SOLVABLE":
        # 1. Every clue must be truthful under hidden solution
        for ch in puzzle.characters:
            assert evaluate_clue_truth(ch.hidden_clue, hidden_bool, puzzle.grid_size), (
                f"{puzzle.puzzle_id}: clue {ch.hidden_clue.clue_id} is FALSE on hidden solution"
            )

        # 2. Complete clue set must have a strictly unique solution matching hidden_status
        uniq = oracle.check_uniqueness(engine.get_all_clues_for_uniqueness(), puzzle.grid_size)
        assert uniq.is_unique, f"{puzzle.puzzle_id}: uniqueness failed ({uniq.solution_count_status})"
        assert dict(uniq.first_model or {}) == hidden_status

        # 3. Full GameEngine + no-guess entailment must solve the entire board cleanly
        trace = oracle.run_auto_solve(engine)
        final_state = engine.get_public_state()
        assert final_state.is_solved, f"{puzzle.puzzle_id}: did not solve without guessing"
        assert dict(final_state.proved_verdicts) == hidden_status
        assert all(step.verdict_code == VerdictCode.ACCEPTED for step in trace)

    elif puzzle.expected_status == "AMBIGUOUS":
        # All clues consistent with hidden solution, yet no-guess deduction must halt safely
        for ch in puzzle.characters:
            assert evaluate_clue_truth(ch.hidden_clue, hidden_bool, puzzle.grid_size)
        trace = oracle.run_auto_solve(engine)
        final_state = engine.get_public_state()
        assert not final_state.is_solved
        assert trace[-1].verdict_code == VerdictCode.NOT_PROVABLE
        assert trace[-1].verdict == Status.UNKNOWN

    elif puzzle.expected_status == "INCONSISTENT":
        # Initial KB_0 must immediately be UNSAT
        state0 = engine.get_public_state()
        assert oracle.check_consistency(state0) is False
        first_unsolved = state0.unsolved_cells[0]
        resp = engine.submit_verdict(first_unsolved, Status.CRIMINAL)
        assert resp.code == VerdictCode.INCONSISTENT
        assert resp.revealed_clue is None
    else:
        pytest.fail(f"Unexpected expected_status: {puzzle.expected_status!r}")
