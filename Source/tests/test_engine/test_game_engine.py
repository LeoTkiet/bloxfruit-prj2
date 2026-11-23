"""Unit tests for GameEngine: lifecycle, verdict protocol, highlight, and anti-leakage."""

import json
from pathlib import Path

import pytest

from core.contracts.models import Status, VerdictCode
from engine.game_engine import GameEngine
from tests.test_engine.mock_agent import MockLogicAgent


@pytest.fixture
def sample_2x2_file(tmp_path: Path) -> Path:
    data = {
        "puzzle_id": "unit_2x2",
        "name": "Unit Test 2x2",
        "grid_size": 2,
        "initial_revealed": ["A1"],
        "characters": [
            {
                "cell_id": "A1",
                "name": "Abel",
                "profession": "Astronaut",
                "status": "INNOCENT",
                "clue": {
                    "clue_id": "clue_A1",
                    "type": "EXACTLY",
                    "region": {"type": "ROW", "row": 1},
                    "count": 1,
                },
            },
            {
                "cell_id": "B1",
                "name": "Bea",
                "profession": "Cook",
                "status": "CRIMINAL",
                "clue": {
                    "clue_id": "clue_B1",
                    "type": "FACT",
                    "target": "A2",
                    "target_status": "CRIMINAL",
                },
            },
            {
                "cell_id": "A2",
                "name": "Clara",
                "profession": "Guard",
                "status": "CRIMINAL",
                "clue": {
                    "clue_id": "clue_A2",
                    "type": "DIFFERENT",
                    "targets": ["A2", "B2"],
                },
            },
            {
                "cell_id": "B2",
                "name": "Derek",
                "profession": "Farmer",
                "status": "INNOCENT",
                "clue": {
                    "clue_id": "clue_B2",
                    "type": "EXACTLY",
                    "region": {"type": "COL", "col": "B"},
                    "count": 1,
                },
            },
        ],
    }
    path = tmp_path / "unit_2x2.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_public_state_never_leaks_hidden_statuses_or_face_down_clues(sample_2x2_file: Path) -> None:
    """Dedicated anti-leakage test required by TV1 Definition of Done."""
    agent = MockLogicAgent()
    engine = GameEngine(logic_agent=agent)
    state = engine.load_puzzle(sample_2x2_file)

    assert state.step == 0
    assert not state.is_solved
    assert state.revealed_cells == ("A1",)
    assert state.unsolved_cells == ("B1", "A2", "B2")

    # Only A1 is revealed and visible
    assert dict(state.proved_verdicts) == {"A1": Status.INNOCENT}
    assert len(state.revealed_clues) == 1
    assert state.revealed_clues[0].clue_id == "clue_A1"

    # Face-down cards MUST NOT expose status or clue
    for cid in ("B1", "A2", "B2"):
        ch = state.get_character(cid)
        assert not ch.is_revealed
        assert ch.status == Status.UNKNOWN
        assert ch.clue is None
        assert cid not in state.proved_verdicts

    # Highlight MUST NOT leak targets of face-down clues!
    assert engine.get_highlighted_cells("A1") == ["A1", "B1"]
    assert engine.get_highlighted_cells("B1") == []
    assert engine.get_highlighted_cells("A2") == []
    assert engine.get_highlighted_cells("B2") == []

    # Mutating returned snapshot must fail
    with pytest.raises(TypeError):
        state.proved_verdicts["B1"] = Status.CRIMINAL  # type: ignore[index]


def test_submit_verdict_not_provable_and_contradicted_leave_state_unchanged(
    sample_2x2_file: Path,
) -> None:
    agent = MockLogicAgent(
        consistent=True,
        entailed={"B1": Status.CRIMINAL, "A2": Status.UNKNOWN},
    )
    engine = GameEngine(logic_agent=agent)
    initial_state = engine.load_puzzle(sample_2x2_file)

    # 1. NOT_PROVABLE: A2 is UNKNOWN -> rejected, state unchanged, no clue revealed
    resp_np = engine.submit_verdict("A2", Status.CRIMINAL)
    assert resp_np.code == VerdictCode.NOT_PROVABLE
    assert resp_np.revealed_clue is None
    assert resp_np.public_state == initial_state
    assert engine.get_public_state() == initial_state
    assert engine.get_highlighted_cells("A2") == []

    # 2. CONTRADICTED: B1 is forced CRIMINAL, player submits INNOCENT -> rejected, no leak
    resp_con = engine.submit_verdict("B1", Status.INNOCENT)
    assert resp_con.code == VerdictCode.CONTRADICTED
    assert resp_con.revealed_clue is None
    assert resp_con.public_state == initial_state
    assert engine.get_public_state() == initial_state
    assert engine.get_highlighted_cells("B1") == []

    # Verify MockLogicAgent ONLY ever saw PublicState with zero hidden clues
    for seen in agent.received_states:
        assert len(seen.revealed_clues) == 1
        assert seen.get_character("B1").clue is None
        assert seen.get_character("B1").status == Status.UNKNOWN


def test_submit_verdict_accepted_reveals_card_and_restart_resets(
    sample_2x2_file: Path,
) -> None:
    agent = MockLogicAgent(
        consistent=True,
        entailed={"B1": Status.CRIMINAL, "A2": Status.CRIMINAL, "B2": Status.INNOCENT},
    )
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(sample_2x2_file)

    r1 = engine.submit_verdict("B1", Status.CRIMINAL)
    assert r1.code == VerdictCode.ACCEPTED
    assert r1.revealed_clue is not None and r1.revealed_clue.clue_id == "clue_B1"
    assert r1.public_state.step == 1
    assert r1.public_state.proved_verdicts["B1"] == Status.CRIMINAL
    assert not r1.public_state.is_solved
    # Now B1's clue is revealed, so highlight works for B1
    assert engine.get_highlighted_cells("B1") == ["A2"]

    r2 = engine.submit_verdict("A2", Status.CRIMINAL)
    assert r2.code == VerdictCode.ACCEPTED
    assert r2.public_state.step == 2
    assert engine.get_highlighted_cells("A2") == ["A2", "B2"]

    r3 = engine.submit_verdict("B2", Status.INNOCENT)
    assert r3.code == VerdictCode.ACCEPTED
    assert r3.public_state.step == 3
    assert r3.public_state.is_solved is True

    # Restart must restore step=0 and hide B1, A2, B2 again
    restarted = engine.restart()
    assert restarted.step == 0
    assert not restarted.is_solved
    assert restarted.revealed_cells == ("A1",)
    assert engine.get_highlighted_cells("B1") == []


def test_submit_verdict_inconsistent_kb(sample_2x2_file: Path) -> None:
    agent = MockLogicAgent(consistent=False)
    engine = GameEngine(logic_agent=agent)
    initial = engine.load_puzzle(sample_2x2_file)

    resp = engine.submit_verdict("B1", Status.CRIMINAL)
    assert resp.code == VerdictCode.INCONSISTENT
    assert resp.revealed_clue is None
    assert resp.public_state == initial


def test_submit_verdict_rejects_bad_inputs_and_missing_agent(sample_2x2_file: Path) -> None:
    engine = GameEngine()
    with pytest.raises(RuntimeError):
        engine.get_public_state()

    engine.load_puzzle(sample_2x2_file)
    with pytest.raises(RuntimeError):
        engine.submit_verdict("B1", Status.CRIMINAL)

    engine.set_logic_agent(MockLogicAgent())
    with pytest.raises(ValueError):
        engine.submit_verdict("Z9", Status.CRIMINAL)
    with pytest.raises(ValueError):
        engine.submit_verdict("B1", Status.UNKNOWN)


def test_get_all_clues_for_uniqueness_and_custom_region_resolver(sample_2x2_file: Path) -> None:
    called_with = []

    def custom_resolver(region, grid_size):
        called_with.append((region.region_type, grid_size))
        return ["A1", "B1"]

    engine = GameEngine(logic_agent=MockLogicAgent(), region_resolver=custom_resolver)
    engine.load_puzzle(sample_2x2_file)

    assert engine.get_highlighted_cells("A1") == ["A1", "B1"]
    assert len(called_with) == 1

    # Also test set_region_resolver
    engine.set_region_resolver(lambda r, n: ["A1"])
    assert engine.get_highlighted_cells("A1") == ["A1"]

    with pytest.raises(ValueError):
        engine.get_highlighted_cells("Z9")

    all_clues = engine.get_all_clues_for_uniqueness()
    assert [c.clue_id for c in all_clues] == ["clue_A1", "clue_B1", "clue_A2", "clue_B2"]


def test_submit_verdict_on_already_revealed_card_and_hidden_conflict(
    sample_2x2_file: Path,
) -> None:
    # A1 is already revealed as INNOCENT
    agent = MockLogicAgent(consistent=True, entailed={"B1": Status.INNOCENT})
    engine = GameEngine(logic_agent=agent)
    state0 = engine.load_puzzle(sample_2x2_file)

    # Matching verdict on already revealed card is idempotent (step unchanged)
    same_resp = engine.submit_verdict("A1", Status.INNOCENT)
    assert same_resp.code == VerdictCode.ACCEPTED
    assert same_resp.public_state == state0

    # Opposite verdict on already revealed card returns CONTRADICTED
    opp_resp = engine.submit_verdict("A1", Status.CRIMINAL)
    assert opp_resp.code == VerdictCode.CONTRADICTED
    assert opp_resp.revealed_clue is None
    assert opp_resp.public_state == state0

    # Sanity guard: if agent entails INNOCENT for B1 but hidden truth is CRIMINAL -> INCONSISTENT
    conflict_resp = engine.submit_verdict("B1", Status.INNOCENT)
    assert conflict_resp.code == VerdictCode.INCONSISTENT
    assert conflict_resp.revealed_clue is None
    assert conflict_resp.public_state == state0

