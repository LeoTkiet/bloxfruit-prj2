"""Hint engine tests (TC-HINT-01 through TC-HINT-05)."""

from __future__ import annotations

from agent import DeductiveLogicAgent
from core.contracts.models import Clue, ClueType, RegionSpec, RegionType, Status
from engine.game_engine import GameEngine
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import (
    SpySATSolver,
    make_public_state,
    make_puzzle_definition,
)


def test_tc_hint_01_picks_first_forced_cell_row_major_with_relevant_clues() -> None:
    """TC-HINT-01: Picks B1 (row-major) over C1/A2 and returns scoped revealed clues."""
    clues = (
        Clue(
            "c_A1",
            "A1",
            ClueType.EXACTLY,
            region=RegionSpec(RegionType.EXPLICIT, cells=("B1", "C1", "A2")),
            count=0,
        ),
        Clue("c_unrelated", "C3", ClueType.FACT, target="B3", target_status=Status.INNOCENT),
    )
    state = make_public_state(
        3,
        proved_verdicts={"A1": Status.CRIMINAL, "C3": Status.INNOCENT},
        revealed_clues=clues,
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    hint = agent.get_hint(state)

    assert hint.cell == "B1"
    assert hint.forced_status == Status.INNOCENT
    assert hint.is_inconsistent is False
    assert hint.relevant_clue_ids == ("c_A1",)
    assert "c_unrelated" not in hint.relevant_clue_ids
    assert "B1" in hint.message


def test_tc_hint_01b_transitive_linked_clues_included() -> None:
    """Linked clues sharing unsolved cells with target_cell are included in relevant_clue_ids."""
    clues_linked = (
        Clue("c_A1", "A1", ClueType.FACT, target="B2", target_status=Status.CRIMINAL),
        Clue("c_C1", "C1", ClueType.SAME, targets=("B2", "A2")),
        Clue("c_C3", "C3", ClueType.FACT, target="B3", target_status=Status.INNOCENT),
    )
    state = make_public_state(
        3,
        proved_verdicts={"A1": Status.INNOCENT, "C1": Status.INNOCENT, "C3": Status.INNOCENT},
        revealed_clues=clues_linked,
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    hint = agent.get_hint(state)

    assert hint.cell == "A2"
    assert hint.forced_status == Status.CRIMINAL
    assert set(hint.relevant_clue_ids) == {"c_A1", "c_C1"}
    assert "c_C3" not in hint.relevant_clue_ids


def test_tc_hint_02_does_not_leak_hidden_solution() -> None:
    """TC-HINT-02: Identical PublicStates from puzzles with different hidden truths yield identical hints."""
    clues_p1 = {
        "A1": Clue("c_A1", "A1", ClueType.EXACTLY, region=RegionSpec(RegionType.ROW, row=1), count=1),
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="A2", target_status=Status.CRIMINAL),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A2", target_status=Status.CRIMINAL),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="B2", target_status=Status.INNOCENT),
    }
    clues_p2 = {
        "A1": Clue("c_A1", "A1", ClueType.EXACTLY, region=RegionSpec(RegionType.ROW, row=1), count=1),
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="B2", target_status=Status.CRIMINAL),
    }
    p1 = make_puzzle_definition(
        "p_h1",
        2,
        {"A1": Status.INNOCENT, "B1": Status.CRIMINAL, "A2": Status.CRIMINAL, "B2": Status.INNOCENT},
        clues_p1,
        initial_revealed=("A1",),
    )
    p2 = make_puzzle_definition(
        "p_h2",
        2,
        {"A1": Status.INNOCENT, "B1": Status.CRIMINAL, "A2": Status.INNOCENT, "B2": Status.CRIMINAL},
        clues_p2,
        initial_revealed=("A1",),
    )

    eng1 = GameEngine()
    eng1.load_puzzle_definition(p1)
    eng2 = GameEngine()
    eng2.load_puzzle_definition(p2)

    s1 = eng1.get_public_state()
    s2 = eng2.get_public_state()
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    h1 = agent.get_hint(s1)
    h2 = agent.get_hint(s2)
    assert h1 == h2
    assert h1.cell == "B1"

    # Now on an ambiguous PublicState where hidden truth differs on A2/B2:
    amb_clues_a = {
        "A1": Clue("c_A1", "A1", ClueType.AT_LEAST, region=RegionSpec(RegionType.ROW, row=1), count=0),
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="B1", target_status=Status.CRIMINAL),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A2", target_status=Status.CRIMINAL),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="B2", target_status=Status.INNOCENT),
    }
    amb_clues_b = {
        "A1": Clue("c_A1", "A1", ClueType.AT_LEAST, region=RegionSpec(RegionType.ROW, row=1), count=0),
        "B1": Clue("c_B1", "B1", ClueType.FACT, target="B1", target_status=Status.INNOCENT),
        "A2": Clue("c_A2", "A2", ClueType.FACT, target="A2", target_status=Status.INNOCENT),
        "B2": Clue("c_B2", "B2", ClueType.FACT, target="B2", target_status=Status.CRIMINAL),
    }
    pa = make_puzzle_definition(
        "amb_1", 2,
        {"A1": Status.INNOCENT, "B1": Status.CRIMINAL, "A2": Status.CRIMINAL, "B2": Status.INNOCENT},
        amb_clues_a, initial_revealed=("A1",), expected_status="AMBIGUOUS",
    )
    pb = make_puzzle_definition(
        "amb_2", 2,
        {"A1": Status.INNOCENT, "B1": Status.INNOCENT, "A2": Status.INNOCENT, "B2": Status.CRIMINAL},
        amb_clues_b, initial_revealed=("A1",), expected_status="AMBIGUOUS",
    )
    ea, eb = GameEngine(), GameEngine()
    ea.load_puzzle_definition(pa)
    eb.load_puzzle_definition(pb)
    ha = agent.get_hint(ea.get_public_state())
    hb = agent.get_hint(eb.get_public_state())
    assert ha == hb
    assert ha.cell is None and ha.forced_status == Status.UNKNOWN


def test_tc_hint_03_ambiguous_state_returns_unknown_with_relevant_clues() -> None:
    """TC-HINT-03: Ambiguous KB returns cell=None, UNKNOWN, relevant clues, AMBIGUOUS message."""
    clue = Clue(
        "c_A1",
        "A1",
        ClueType.SAME,
        targets=("B1", "A2"),
    )
    state = make_public_state(
        2,
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(clue,),
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    hint = agent.get_hint(state)

    assert hint.cell is None
    assert hint.forced_status == Status.UNKNOWN
    assert hint.is_inconsistent is False
    assert hint.relevant_clue_ids == ("c_A1",)
    assert "AMBIGUOUS" in hint.message


def test_tc_hint_04_already_solved_board_uses_zero_sat_calls() -> None:
    """TC-HINT-04: Solved board returns UNKNOWN with 0 SAT solver calls."""
    spy = SpySATSolver(make_solver())
    agent = DeductiveLogicAgent(StubCNFEncoder(), spy)
    solved = make_public_state(
        2,
        proved_verdicts={
            "A1": Status.CRIMINAL,
            "B1": Status.INNOCENT,
            "A2": Status.INNOCENT,
            "B2": Status.CRIMINAL,
        },
    )
    hint = agent.get_hint(solved)

    assert hint.cell is None
    assert hint.forced_status == Status.UNKNOWN
    assert hint.is_inconsistent is False
    assert spy.call_count == 0
    assert agent.stats.deduction_sat_calls == 0


def test_tc_hint_05_inconsistent_kb_returns_is_inconsistent_true() -> None:
    """TC-HINT-05: Inconsistent KB returns is_inconsistent=True and INCONSISTENT message."""
    clue = Clue("c_bad", "A1", ClueType.FACT, target="A1", target_status=Status.INNOCENT)
    state = make_public_state(
        2,
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=(clue,),
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    hint = agent.get_hint(state)

    assert hint.cell is None
    assert hint.forced_status == Status.UNKNOWN
    assert hint.is_inconsistent is True
    assert "INCONSISTENT" in hint.message
