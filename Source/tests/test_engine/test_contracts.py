"""Unit tests for frozen shared contracts (`core/contracts/models.py` & `interfaces.py`)."""

from dataclasses import FrozenInstanceError

import pytest

from core.contracts import (
    CharacterPublicInfo,
    Clue,
    ClueType,
    CNFFormula,
    IGameEngine,
    ILogicAgent,
    PublicState,
    SATResult,
    Status,
    UniquenessResult,
    all_cell_ids,
    col_index_to_letter,
    col_letter_to_index,
    coords_to_cell_id,
    parse_cell_id,
)
from engine.game_engine import GameEngine
from tests.test_engine.mock_agent import MockLogicAgent


def test_coordinate_helpers_roundtrip() -> None:
    assert col_index_to_letter(0) == "A"
    assert col_index_to_letter(4) == "E"
    assert col_letter_to_index("C") == 2
    assert coords_to_cell_id(1, 2) == "C2"
    assert parse_cell_id("C2") == (1, 2)
    assert all_cell_ids(3) == ("A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3")


def test_coordinate_helpers_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        parse_cell_id("C0")
    with pytest.raises(ValueError):
        parse_cell_id("12")
    with pytest.raises(ValueError):
        parse_cell_id("a1")
    with pytest.raises(ValueError):
        col_index_to_letter(26)


def test_character_public_info_enforces_no_hidden_leakage() -> None:
    sample_clue = Clue(
        clue_id="c1",
        owner="A1",
        clue_type=ClueType.FACT,
        target="B1",
        target_status=Status.CRIMINAL,
    )
    # Face-down character CANNOT expose a non-UNKNOWN status
    with pytest.raises(ValueError):
        CharacterPublicInfo("A1", "Abel", "Cook", Status.CRIMINAL, is_revealed=False, clue=None)

    # Face-down character CANNOT expose a clue
    with pytest.raises(ValueError):
        CharacterPublicInfo("A1", "Abel", "Cook", Status.UNKNOWN, is_revealed=False, clue=sample_clue)

    # Face-up character CANNOT have UNKNOWN status
    with pytest.raises(ValueError):
        CharacterPublicInfo("A1", "Abel", "Cook", Status.UNKNOWN, is_revealed=True, clue=sample_clue)


def test_public_state_and_contracts_are_deeply_immutable() -> None:
    c_a1 = CharacterPublicInfo("A1", "Abel", "Cook", Status.INNOCENT, True, None)
    c_b1 = CharacterPublicInfo("B1", "Bea", "Guard", Status.UNKNOWN, False, None)
    state = PublicState(
        puzzle_id="p1",
        puzzle_name="Test",
        grid_size=2,
        step=0,
        characters=(c_a1, c_b1),
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(),
        is_solved=False,
    )

    with pytest.raises(FrozenInstanceError):
        state.step = 99  # type: ignore[misc]
    with pytest.raises(TypeError):
        state.proved_verdicts["B1"] = Status.CRIMINAL  # type: ignore[index]

    assert state.revealed_cells == ("A1",)
    assert state.unsolved_cells == ("B1",)
    assert state.get_character("A1") == c_a1

    cnf = CNFFormula(clauses=((1, -2),), num_primary_vars=2, num_aux_vars=1, var_to_cell={1: "A1"})
    assert cnf.num_vars == 3
    assert cnf.num_clauses == 1
    with pytest.raises(TypeError):
        cnf.var_to_cell[2] = "B1"  # type: ignore[index]

    sat_res = SATResult(is_sat=True, model={1: True, 2: False})
    with pytest.raises(TypeError):
        sat_res.model[1] = False  # type: ignore[index]

    uniq = UniquenessResult(is_unique=True, solution_count_status="UNIQUE", first_model={"A1": Status.INNOCENT})
    with pytest.raises(TypeError):
        uniq.first_model["A1"] = Status.CRIMINAL  # type: ignore[index]


def test_protocol_runtime_conformance() -> None:
    assert isinstance(GameEngine(), IGameEngine)
    assert isinstance(MockLogicAgent(), ILogicAgent)
