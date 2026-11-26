"""Uniqueness verification tests (TC-UNIQ-01 through TC-UNIQ-05 + real puzzles)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent import DeductiveLogicAgent, check_uniqueness
from core.contracts.models import Clue, ClueType, RegionSpec, RegionType, Status
from engine.game_engine import GameEngine
from engine.puzzle_loader import load_puzzle_definition
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import PUZZLES_DIR, SpySATSolver
from tests.test_engine.mock_agent import evaluate_clue_truth

SOLVABLE_PUZZLES = sorted(
    list((PUZZLES_DIR / "3x3").glob("*.json"))
    + list((PUZZLES_DIR / "4x4").glob("*.json"))
    + list((PUZZLES_DIR / "5x5").glob("*.json"))
    + list((PUZZLES_DIR / "extensions").glob("*.json"))
)


def test_tc_uniq_01_unsat_clue_set() -> None:
    """TC-UNIQ-01: Contradictory clue set returns UNSAT with exactly 1 SAT call."""
    spy = SpySATSolver(make_solver())
    clues = [
        Clue("c1", "A1", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        Clue("c2", "B1", ClueType.FACT, target="A1", target_status=Status.INNOCENT),
    ]
    res = check_uniqueness(clues, 2, StubCNFEncoder(), spy)

    assert res.is_unique is False
    assert res.solution_count_status == "UNSAT"
    assert res.first_model is None
    assert res.second_model is None
    assert res.metrics_first is not None
    assert res.metrics_second is None
    assert spy.call_count == 1


def test_tc_uniq_02_unique_clue_set_calls_solver_twice() -> None:
    """TC-UNIQ-02: Uniquely determined 2x2 clue set returns UNIQUE in 2 SAT calls."""
    spy = SpySATSolver(make_solver())
    clues = [
        Clue("c1", "A1", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        Clue("c2", "B1", ClueType.DIFFERENT, targets=("A1", "B1")),
        Clue("c3", "A2", ClueType.SAME, targets=("A1", "A2")),
        Clue("c4", "B2", ClueType.DIFFERENT, targets=("A2", "B2")),
    ]
    res = check_uniqueness(clues, 2, StubCNFEncoder(), spy)

    assert res.is_unique is True
    assert res.solution_count_status == "UNIQUE"
    assert dict(res.first_model or {}) == {
        "A1": Status.CRIMINAL,
        "B1": Status.INNOCENT,
        "A2": Status.CRIMINAL,
        "B2": Status.INNOCENT,
    }
    assert res.second_model is None
    assert res.metrics_first is not None
    assert res.metrics_second is not None
    assert spy.call_count == 2


def test_tc_uniq_03_multiple_solutions_clue_set() -> None:
    """TC-UNIQ-03: Under-constrained clue set returns MULTIPLE with 2 distinct models."""
    clues = [
        Clue("c1", "A1", ClueType.DIFFERENT, targets=("A1", "B1")),
        Clue("c2", "B1", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        Clue("c3", "A2", ClueType.FACT, target="B2", target_status=Status.INNOCENT),
    ]
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    res = agent.check_uniqueness(clues, 2)

    assert res.is_unique is False
    assert res.solution_count_status == "MULTIPLE"
    assert res.first_model is not None
    assert res.second_model is not None
    assert dict(res.first_model) != dict(res.second_model)

    for model in (res.first_model, res.second_model):
        bool_assign = {k: (v == Status.CRIMINAL) for k, v in model.items()}
        for clue in clues:
            assert evaluate_clue_truth(clue, bool_assign, 2)


def test_tc_uniq_04_blocking_clause_ignores_auxiliary_variables() -> None:
    """TC-UNIQ-04: Free auxiliary variables must NOT cause false MULTIPLE result."""
    encoder_with_free_aux = StubCNFEncoder(inject_free_aux_vars=3)
    clues = [
        Clue("c1", "A1", ClueType.FACT, target="A1", target_status=Status.INNOCENT),
        Clue("c2", "B1", ClueType.FACT, target="B1", target_status=Status.CRIMINAL),
        Clue("c3", "A2", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        Clue("c4", "B2", ClueType.FACT, target="B2", target_status=Status.CRIMINAL),
    ]
    res = check_uniqueness(clues, 2, encoder_with_free_aux, make_solver())

    assert res.is_unique is True
    assert res.solution_count_status == "UNIQUE"


def test_tc_uniq_05_does_not_mutate_input_clues() -> None:
    """TC-UNIQ-05: Input clue sequence is untouched and metrics are populated."""
    clues = [
        Clue("c1", "A1", ClueType.EXACTLY, region=RegionSpec(RegionType.ROW, row=1), count=1),
        Clue("c2", "B1", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        Clue("c3", "A2", ClueType.EXACTLY, region=RegionSpec(RegionType.COL, col="A"), count=2),
        Clue("c4", "B2", ClueType.FACT, target="B2", target_status=Status.INNOCENT),
    ]
    snapshot = list(clues)
    res = check_uniqueness(clues, 2, StubCNFEncoder(), make_solver())
    assert clues == snapshot
    assert res.is_unique is True
    assert res.metrics_first is not None and res.metrics_second is not None


@pytest.mark.parametrize(
    "puzzle_path",
    SOLVABLE_PUZZLES,
    ids=[p.relative_to(PUZZLES_DIR).as_posix() for p in SOLVABLE_PUZZLES],
)
def test_real_solvable_puzzles_are_unique_and_match_hidden_solution(
    puzzle_path: Path,
) -> None:
    """All 13 solvable puzzles (10 standard + 3 extensions) are UNIQUE."""
    puzzle = load_puzzle_definition(puzzle_path)
    hidden_status = {ch.cell_id: ch.hidden_status for ch in puzzle.characters}

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(puzzle_path)

    res = agent.check_uniqueness(engine.get_all_clues_for_uniqueness(), puzzle.grid_size)
    assert res.is_unique is True
    assert res.solution_count_status == "UNIQUE"
    assert dict(res.first_model or {}) == hidden_status


def test_inconsistent_edge_puzzle_is_unsat_under_uniqueness() -> None:
    """edge_3x3_02_inconsistent has contradictory clues -> UNSAT."""
    puzzle_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_02_inconsistent.json"
    puzzle = load_puzzle_definition(puzzle_path)
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(puzzle_path)

    res = agent.check_uniqueness(engine.get_all_clues_for_uniqueness(), puzzle.grid_size)
    assert res.is_unique is False
    assert res.solution_count_status == "UNSAT"
