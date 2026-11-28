"""Entailment unit tests (TC-ENT-01 through TC-ENT-07)."""

from __future__ import annotations

from agent import DeductiveLogicAgent
from core.contracts.models import (
    Clue,
    ClueType,
    CNFFormula,
    CNFStats,
    PublicState,
    RegionSpec,
    RegionType,
    Status,
)
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import SpySATSolver, make_public_state


class _CustomFormulaEncoder(StubCNFEncoder):
    """Test helper allowing raw clauses for exact textbook entailment cases."""

    def __init__(self, raw_clauses: tuple[tuple[int, ...], ...]) -> None:
        super().__init__()
        self._raw_clauses = raw_clauses

    def encode_kb(self, public_state: PublicState) -> tuple[CNFFormula, CNFStats]:
        n2 = public_state.grid_size * public_state.grid_size
        cnf = CNFFormula(
            clauses=self._raw_clauses,
            num_primary_vars=n2,
            num_aux_vars=0,
        )
        stats = CNFStats(
            num_primary_vars=n2,
            num_aux_vars=0,
            num_clauses=len(self._raw_clauses),
            encoding_strategy="stub",
        )
        return cnf, stats


def test_tc_ent_01_textbook_entailment_example() -> None:
    """TC-ENT-01: KB = (A1 v B1) & (~A1 v B1) -> B1=CRIMINAL, A1=UNKNOWN."""
    encoder = _CustomFormulaEncoder(((1, 2), (-1, 2)))
    agent = DeductiveLogicAgent(encoder, make_solver())
    state = make_public_state(2, proved_verdicts={"A2": Status.INNOCENT, "B2": Status.INNOCENT})

    assert agent.check_consistency(state) is True
    assert agent.classify_character(state, "B1") == Status.CRIMINAL
    assert agent.classify_character(state, "A1") == Status.UNKNOWN

    all_res = agent.classify_all(state)
    assert all_res == {"A1": Status.UNKNOWN, "B1": Status.CRIMINAL}


def test_tc_ent_02_forced_innocent() -> None:
    """TC-ENT-02: A1=INNOCENT and SAME(A1, B1) forces B1=INNOCENT."""
    clue = Clue(
        clue_id="c_a1",
        owner="A1",
        clue_type=ClueType.SAME,
        targets=("A1", "B1"),
    )
    state = make_public_state(
        2,
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(clue,),
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    assert agent.check_consistency(state) is True
    assert agent.classify_character(state, "B1") == Status.INNOCENT


def test_tc_ent_03_distinguish_satisfying_model_from_logical_consequence() -> None:
    """TC-ENT-03: KB = (A1 v B1) is SAT with A1=T,B1=F, yet neither is entailed."""
    encoder = _CustomFormulaEncoder(((1, 2),))
    agent = DeductiveLogicAgent(encoder, make_solver())
    state = make_public_state(2, proved_verdicts={"A2": Status.INNOCENT, "B2": Status.INNOCENT})

    assert agent.check_consistency(state) is True
    assert agent.classify_all(state) == {"A1": Status.UNKNOWN, "B1": Status.UNKNOWN}


def test_tc_ent_04_inconsistent_kb_detected_before_entailment() -> None:
    """TC-ENT-04: Proved A1=CRIMINAL + FACT(A1=INNOCENT) -> check_consistency=False."""
    clue = Clue(
        clue_id="c_bad",
        owner="A1",
        clue_type=ClueType.FACT,
        target="A1",
        target_status=Status.INNOCENT,
    )
    state = make_public_state(
        2,
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=(clue,),
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())

    assert agent.check_consistency(state) is False
    # Must NOT fall into ex falso quodlibet and falsely report CRIMINAL
    assert agent.classify_character(state, "B1") == Status.UNKNOWN
    assert agent.classify_all(state) == {}

    # Also test cold-cache classify_character directly without calling check_consistency first
    cold_agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    assert cold_agent.classify_character(state, "B1") == Status.UNKNOWN


def test_tc_ent_05_uninformative_kb_all_unknown() -> None:
    """TC-ENT-05: Tautological AT_LEAST(0, ROW 1) leaves all unsolved cells UNKNOWN."""
    clue = Clue(
        clue_id="c_taut",
        owner="A1",
        clue_type=ClueType.AT_LEAST,
        region=RegionSpec(region_type=RegionType.ROW, row=1),
        count=0,
    )
    state = make_public_state(
        3,
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(clue,),
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    assert agent.check_consistency(state) is True
    classified = agent.classify_all(state)
    assert len(classified) == 8
    assert all(st == Status.UNKNOWN for st in classified.values())


def test_tc_ent_06_multi_hop_chain_deduction() -> None:
    """TC-ENT-06: A1=CRIMINAL, SAME(A1,B1), DIFFERENT(B1,C1), EXACTLY(2,{A1,B1,C1,A2})."""
    clues = (
        Clue("c1", "A1", ClueType.SAME, targets=("A1", "B1")),
        Clue("c2", "A1", ClueType.DIFFERENT, targets=("B1", "C1")),
        Clue(
            "c3",
            "A1",
            ClueType.EXACTLY,
            region=RegionSpec(
                region_type=RegionType.EXPLICIT,
                cells=("A1", "B1", "C1", "A2"),
            ),
            count=2,
        ),
    )
    state = make_public_state(
        3,
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=clues,
    )
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    res = agent.classify_all(state)
    assert res["B1"] == Status.CRIMINAL
    assert res["C1"] == Status.INNOCENT
    assert res["A2"] == Status.INNOCENT


def test_tc_ent_07_already_solved_cells_and_board() -> None:
    """TC-ENT-07: classify_all returns only unsolved cells; 0 SAT calls when solved."""
    spy = SpySATSolver(make_solver())
    agent = DeductiveLogicAgent(StubCNFEncoder(), spy)

    fully_solved = make_public_state(
        2,
        proved_verdicts={
            "A1": Status.CRIMINAL,
            "B1": Status.INNOCENT,
            "A2": Status.INNOCENT,
            "B2": Status.CRIMINAL,
        },
    )
    assert agent.classify_all(fully_solved) == {}
    # Consistency check may take 1 call, but 0 per-cell calls are made
    assert spy.call_count <= 1

    # Partially solved board: classify_all excludes already proved cells
    partial = make_public_state(
        2,
        proved_verdicts={"A1": Status.CRIMINAL, "B1": Status.INNOCENT},
    )
    res = agent.classify_all(partial)
    assert set(res.keys()) == {"A2", "B2"}
    assert agent.classify_character(partial, "A1") == Status.CRIMINAL
