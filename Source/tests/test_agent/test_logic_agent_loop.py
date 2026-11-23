"""Deduction loop, outcome, isolation, and real-puzzle integration tests (TC-LOOP-01..09)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from agent import AutoSolveOutcome, DeductiveLogicAgent, outcome_of
from core.contracts.interfaces import IGameEngine, ILogicAgent
from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    DeductionStep,
    RegionSpec,
    RegionType,
    Status,
    VerdictCode,
    VerdictResponse,
)
from engine.game_engine import GameEngine
from engine.puzzle_loader import load_puzzle_definition
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import (
    PUZZLES_DIR,
    IsolationTrapGameEngine,
    make_puzzle_definition,
)

STANDARD_PUZZLES = sorted(
    list((PUZZLES_DIR / "3x3").glob("*.json"))
    + list((PUZZLES_DIR / "4x4").glob("*.json"))
    + list((PUZZLES_DIR / "5x5").glob("*.json"))
)
EXTENSION_PUZZLES = sorted((PUZZLES_DIR / "extensions").glob("*.json"))
SOLVABLE_PUZZLES = STANDARD_PUZZLES + EXTENSION_PUZZLES


def test_agent_implements_ilogicagent_protocol() -> None:
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    assert isinstance(agent, ILogicAgent)


def test_tc_loop_01_happy_path_3x3_and_zero_validation_calls() -> None:
    """TC-LOOP-01: Solve 3x3_01 cleanly with 8 steps and validation_sat_calls == 0."""
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    puzzle = load_puzzle_definition(puzzle_path)
    hidden_status = {ch.cell_id: ch.hidden_status for ch in puzzle.characters}

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(puzzle_path)

    steps = agent.run_auto_solve(engine)
    final_state = engine.get_public_state()

    assert final_state.is_solved is True
    assert dict(final_state.proved_verdicts) == hidden_status
    assert len(steps) == 9 - len(puzzle.initial_revealed)
    assert [s.step_number for s in steps] == list(range(1, len(steps) + 1))
    assert all(s.verdict_code == VerdictCode.ACCEPTED for s in steps)
    assert all(s.revealed_clue is not None for s in steps)
    assert all(s.cnf_stats is not None for s in steps)
    assert all(len(s.sat_queries) >= 1 for s in steps)
    assert agent.last_outcome == AutoSolveOutcome.SOLVED
    assert outcome_of(steps, final_state) == AutoSolveOutcome.SOLVED
    assert agent.stats.validation_sat_calls == 0
    assert agent.stats.deduction_sat_calls > 0


def test_tc_loop_02_multiple_initial_revealed_cards() -> None:
    """TC-LOOP-02: 3x3 puzzle starting with 3 revealed cards finishes in 6 steps."""
    statuses = {
        "A1": Status.CRIMINAL, "B1": Status.INNOCENT, "C1": Status.CRIMINAL,
        "A2": Status.INNOCENT, "B2": Status.CRIMINAL, "C2": Status.INNOCENT,
        "A3": Status.CRIMINAL, "B3": Status.INNOCENT, "C3": Status.CRIMINAL,
    }
    clues = {
        "A1": Clue("c_A1", "A1", ClueType.FACT, target="B1", target_status=Status.INNOCENT),
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="C1", target_status=Status.CRIMINAL),
        "C1": Clue("c_C1", "C1", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="B2", target_status=Status.CRIMINAL),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="C2", target_status=Status.INNOCENT),
        "C2": Clue("c_C2", "C2", ClueType.FACT, target="A3", target_status=Status.CRIMINAL),
        "A3": Clue("c_A3", "A3", ClueType.FACT, target="B3", target_status=Status.INNOCENT),
        "B3": Clue("c_B3", "B3", ClueType.FACT, target="C3", target_status=Status.CRIMINAL),
        "C3": Clue("c_C3", "C3", ClueType.AT_LEAST, region=RegionSpec(RegionType.ROW, row=1), count=1),
    }
    puzzle = make_puzzle_definition(
        "multi_init_3x3", 3, statuses, clues, initial_revealed=("A1", "B1", "A2")
    )

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle_definition(puzzle)

    steps = agent.run_auto_solve(engine)
    assert len(steps) == 6
    assert set(steps[0].active_clue_ids) == {"c_A1", "c_B1", "c_A2"}
    assert agent.last_outcome == AutoSolveOutcome.SOLVED
    assert agent.stats.validation_sat_calls == 0


def test_tc_loop_03_deterministic_row_major_selection() -> None:
    """TC-LOOP-03: When C1, A2, B1 are all forced, B1 is picked first (not A2)."""
    statuses = {
        "A1": Status.CRIMINAL, "B1": Status.INNOCENT, "C1": Status.INNOCENT,
        "A2": Status.INNOCENT, "B2": Status.INNOCENT, "C2": Status.INNOCENT,
        "A3": Status.INNOCENT, "B3": Status.INNOCENT, "C3": Status.INNOCENT,
    }
    clues = {
        "A1": Clue("c_A1", "A1", ClueType.EXACTLY, region=RegionSpec(RegionType.EXPLICIT, cells=("B1", "C1", "A2")), count=0),
        "B1": Clue("c_B1", "B1", ClueType.EXACTLY, region=RegionSpec(RegionType.ROW, row=2), count=0),
        "C1": Clue("c_C1", "C1", ClueType.EXACTLY, region=RegionSpec(RegionType.ROW, row=3), count=0),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "C2": Clue("c_C2", "C2", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "A3": Clue("c_A3", "A3", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "B3": Clue("c_B3", "B3", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "C3": Clue("c_C3", "C3", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
    }
    puzzle = make_puzzle_definition("tie_break", 3, statuses, clues, initial_revealed=("A1",))

    traces = []
    for _ in range(3):
        agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
        engine = GameEngine(logic_agent=agent)
        engine.load_puzzle_definition(puzzle)
        steps = agent.run_auto_solve(engine)
        traces.append([(s.cell, s.verdict) for s in steps])

    # B1 must be chosen before C1 and A2 (even though 'A2' < 'B1' alphabetically)
    assert traces[0][0] == ("B1", Status.INNOCENT)
    assert traces[0][1] == ("C1", Status.INNOCENT)
    assert traces[0] == traces[1] == traces[2]


def test_tc_loop_04_ambiguous_stops_without_guessing_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TC-LOOP-04: edge_3x3_01_ambiguous halts at AMBIGUOUS with convention terminal step & warning."""
    puzzle_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_01_ambiguous.json"
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    real_engine = GameEngine(logic_agent=agent)
    real_engine.load_puzzle(puzzle_path)
    trap_engine = IsolationTrapGameEngine(real_engine)

    with caplog.at_level(logging.WARNING, logger="agent"):
        steps = agent.run_auto_solve(trap_engine)

    final_state = real_engine.get_public_state()
    assert not final_state.is_solved
    assert agent.last_outcome == AutoSolveOutcome.AMBIGUOUS
    assert outcome_of(steps, final_state) == AutoSolveOutcome.AMBIGUOUS

    last = steps[-1]
    assert last.cell is None
    assert last.verdict == Status.UNKNOWN
    assert last.verdict_code == VerdictCode.NOT_PROVABLE
    assert last.revealed_clue is None
    assert set(last.active_clue_ids) == {c.clue_id for c in final_state.revealed_clues}

    # No guess was ever submitted for remaining unknown cells
    assert len(trap_engine.submitted_verdicts) == len(steps) - 1
    assert agent.stats.validation_sat_calls == 0

    # Warning logged with puzzle_id, step, unknown cells
    warning_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "edge_3x3_ambiguous" in m and "step=" in m and "unknown_cells=" in m
        for m in warning_msgs
    )


def test_tc_loop_05_inconsistent_kb0_stops_immediately() -> None:
    """TC-LOOP-05: edge_3x3_02_inconsistent stops at step 1 with INCONSISTENT."""
    puzzle_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_02_inconsistent.json"
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    real_engine = GameEngine(logic_agent=agent)
    real_engine.load_puzzle(puzzle_path)
    trap_engine = IsolationTrapGameEngine(real_engine)

    steps = agent.run_auto_solve(trap_engine)
    final_state = real_engine.get_public_state()

    assert len(steps) == 1
    assert steps[0].cell is None
    assert steps[0].verdict == Status.UNKNOWN
    assert steps[0].verdict_code == VerdictCode.INCONSISTENT
    assert trap_engine.submitted_verdicts == []
    assert agent.last_outcome == AutoSolveOutcome.INCONSISTENT
    assert outcome_of(steps, final_state) == AutoSolveOutcome.INCONSISTENT


def test_tc_loop_06_mid_solve_inconsistency_detected() -> None:
    """TC-LOOP-06: Step 1 reveals B1 whose clue contradicts KB_1 -> step 2 INCONSISTENT."""
    statuses = {
        "A1": Status.INNOCENT, "B1": Status.CRIMINAL,
        "A2": Status.CRIMINAL, "B2": Status.INNOCENT,
    }
    clues = {
        "A1": Clue("c_A1", "A1", ClueType.FACT, target="B1", target_status=Status.CRIMINAL),
        # Contradicts revealed A1=INNOCENT once B1 is flipped
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="A1", target_status=Status.CRIMINAL),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A2", target_status=Status.CRIMINAL),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="B2", target_status=Status.INNOCENT),
    }
    puzzle = make_puzzle_definition("mid_inconsistent", 2, statuses, clues, initial_revealed=("A1",))

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle_definition(puzzle)

    steps = agent.run_auto_solve(engine)
    assert len(steps) == 2
    assert steps[0].verdict_code == VerdictCode.ACCEPTED
    assert steps[0].cell == "B1"
    assert steps[1].verdict_code == VerdictCode.INCONSISTENT
    assert steps[1].cell is None
    assert steps[1].verdict == Status.UNKNOWN
    assert agent.last_outcome == AutoSolveOutcome.INCONSISTENT


def test_tc_loop_07_on_step_callback_and_exception_resilience() -> None:
    """TC-LOOP-07: on_step receives every step in order; callback error never breaks agent."""
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    expected_steps = 9 - len(load_puzzle_definition(puzzle_path).initial_revealed)

    # 1. Normal spy callback
    agent1 = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine1 = GameEngine(logic_agent=agent1)
    engine1.load_puzzle(puzzle_path)
    recorded: list[DeductionStep] = []
    steps1 = agent1.run_auto_solve(engine1, on_step=recorded.append)
    assert recorded == steps1
    assert len(recorded) == expected_steps

    # 2. Ambiguous callback receives terminal step too
    ambig_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_01_ambiguous.json"
    agent_amb = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    eng_amb = GameEngine(logic_agent=agent_amb)
    eng_amb.load_puzzle(ambig_path)
    recorded_amb: list[DeductionStep] = []
    steps_amb = agent_amb.run_auto_solve(eng_amb, on_step=recorded_amb.append)
    assert recorded_amb == steps_amb
    assert recorded_amb[-1].verdict_code == VerdictCode.NOT_PROVABLE

    # 3. Inconsistent callback receives terminal step too
    inc_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_02_inconsistent.json"
    agent_inc = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    eng_inc = GameEngine(logic_agent=agent_inc)
    eng_inc.load_puzzle(inc_path)
    recorded_inc: list[DeductionStep] = []
    steps_inc = agent_inc.run_auto_solve(eng_inc, on_step=recorded_inc.append)
    assert recorded_inc == steps_inc
    assert len(recorded_inc) == 1
    assert recorded_inc[0].verdict_code == VerdictCode.INCONSISTENT

    # 4. Failing callback must not break solve or corrupt agent state
    agent2 = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine2 = GameEngine(logic_agent=agent2)
    engine2.load_puzzle(puzzle_path)

    def exploding_callback(step: DeductionStep) -> None:
        raise RuntimeError(f"UI exploded on step {step.step_number}")

    steps2 = agent2.run_auto_solve(engine2, on_step=exploding_callback)
    assert len(steps2) == expected_steps
    assert engine2.get_public_state().is_solved is True
    assert agent2.last_outcome == AutoSolveOutcome.SOLVED


def test_tc_loop_08_strict_hidden_data_isolation() -> None:
    """TC-LOOP-08: Agent never touches hidden attributes or get_all_clues_for_uniqueness."""
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_02_neighbor_chain.json"
    expected_steps = 9 - len(load_puzzle_definition(puzzle_path).initial_revealed)
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    real_engine = GameEngine(logic_agent=agent)
    real_engine.load_puzzle(puzzle_path)
    trap = IsolationTrapGameEngine(real_engine)

    steps = agent.run_auto_solve(trap)
    assert len(steps) == expected_steps
    assert trap.uniqueness_accessor_called is False
    assert trap.forbidden_accesses == []
    assert agent.last_outcome == AutoSolveOutcome.SOLVED


def test_tc_loop_09_infinite_loop_guard_on_unexpected_rejection() -> None:
    """TC-LOOP-09: Unexpected NOT_PROVABLE/CONTRADICTED from engine stops loop safely."""
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    real_engine = GameEngine(logic_agent=agent)
    real_engine.load_puzzle(puzzle_path)

    def reject_verdict(cell: CellID, status: Status, eng: IGameEngine) -> VerdictResponse:
        return VerdictResponse(
            code=VerdictCode.NOT_PROVABLE,
            cell=cell,
            submitted_status=status,
            public_state=eng.get_public_state(),
            revealed_clue=None,
            message="Forced rejection for TC-LOOP-09",
        )

    trap = IsolationTrapGameEngine(real_engine, override_submit=reject_verdict)
    steps = agent.run_auto_solve(trap)

    assert len(steps) == 1
    assert steps[0].verdict_code == VerdictCode.NOT_PROVABLE
    assert not real_engine.get_public_state().is_solved
    assert agent.last_outcome == AutoSolveOutcome.AMBIGUOUS


@pytest.mark.parametrize(
    "puzzle_path",
    SOLVABLE_PUZZLES,
    ids=[p.relative_to(PUZZLES_DIR).as_posix() for p in SOLVABLE_PUZZLES],
)
def test_integration_all_13_solvable_puzzles_with_real_engine_and_dpll(
    puzzle_path: Path,
) -> None:
    """Solve all 10 standard + 3 extension puzzles end-to-end with 0 guesses & 0 validation SAT calls."""
    puzzle = load_puzzle_definition(puzzle_path)
    hidden_status = {ch.cell_id: ch.hidden_status for ch in puzzle.characters}

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(puzzle_path)

    steps = agent.run_auto_solve(engine)
    final_state = engine.get_public_state()

    assert final_state.is_solved is True
    assert dict(final_state.proved_verdicts) == hidden_status
    assert agent.last_outcome == AutoSolveOutcome.SOLVED
    assert outcome_of(steps, final_state) == AutoSolveOutcome.SOLVED
    assert all(s.verdict_code == VerdictCode.ACCEPTED for s in steps)
    assert agent.stats.validation_sat_calls == 0
