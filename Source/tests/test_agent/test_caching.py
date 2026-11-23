"""Model caching and KB LRU caching tests (TC-CACHE-01 through TC-CACHE-04)."""

from __future__ import annotations

from agent import AutoSolveOutcome, DeductiveLogicAgent
from agent.kb_cache import KBCache, KBCacheEntry, make_kb_key
from core.contracts.models import (
    Clue,
    ClueType,
    CNFFormula,
    CNFStats,
    RegionSpec,
    RegionType,
    SATMetrics,
    Status,
)
from engine.game_engine import GameEngine
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import PUZZLES_DIR, SpySATSolver, make_public_state


def test_tc_cache_01_model_cache_enabled_matches_disabled_exactly() -> None:
    """TC-CACHE-01: Classification, trace, and outcome match 100% with caching on vs off."""
    paths = [
        PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json",
        PUZZLES_DIR / "4x4" / "4x4_01_city_grid.json",
        PUZZLES_DIR / "edge_cases" / "edge_3x3_01_ambiguous.json",
        PUZZLES_DIR / "edge_cases" / "edge_3x3_02_inconsistent.json",
    ]

    for path in paths:
        agent_on = DeductiveLogicAgent(StubCNFEncoder(), make_solver(), use_model_cache=True)
        agent_off = DeductiveLogicAgent(StubCNFEncoder(), make_solver(), use_model_cache=False)

        eng_on = GameEngine(logic_agent=agent_on)
        eng_off = GameEngine(logic_agent=agent_off)
        eng_on.load_puzzle(path)
        eng_off.load_puzzle(path)

        steps_on = agent_on.run_auto_solve(eng_on)
        steps_off = agent_off.run_auto_solve(eng_off)

        assert agent_on.last_outcome == agent_off.last_outcome
        assert [(s.cell, s.verdict, s.verdict_code) for s in steps_on] == [
            (s.cell, s.verdict, s.verdict_code) for s in steps_off
        ]
        assert agent_on.stats.validation_sat_calls == 0
        assert agent_off.stats.validation_sat_calls == 0

        real_on = sum(1 for s in steps_on for q in s.sat_queries if not q.cached)
        real_off = sum(1 for s in steps_off for q in s.sat_queries if not q.cached)
        assert real_on <= real_off


def test_tc_cache_02_model_cache_strictly_reduces_sat_calls() -> None:
    """TC-CACHE-02: Weakly constrained 3x3 board has strictly fewer real SAT calls with caching."""
    clue = Clue(
        "c_A1",
        "A1",
        ClueType.AT_LEAST,
        region=RegionSpec(RegionType.ROW, row=1),
        count=1,
    )
    state = make_public_state(
        3,
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(clue,),
    )

    spy_on = SpySATSolver(make_solver())
    spy_off = SpySATSolver(make_solver())
    agent_on = DeductiveLogicAgent(StubCNFEncoder(), spy_on, use_model_cache=True)
    agent_off = DeductiveLogicAgent(StubCNFEncoder(), spy_off, use_model_cache=False)

    res_on = agent_on.classify_all(state)
    res_off = agent_off.classify_all(state)

    assert res_on == res_off
    assert spy_on.call_count < spy_off.call_count
    assert agent_on.stats.deduction_sat_calls == spy_on.call_count
    assert agent_off.stats.deduction_sat_calls == spy_off.call_count

    # Also check DeductionStep logs cached=True entries on ambiguous puzzle
    ambig_path = PUZZLES_DIR / "edge_cases" / "edge_3x3_01_ambiguous.json"
    agent_amb = DeductiveLogicAgent(StubCNFEncoder(), make_solver(), use_model_cache=True)
    eng_amb = GameEngine(logic_agent=agent_amb)
    eng_amb.load_puzzle(ambig_path)
    steps = agent_amb.run_auto_solve(eng_amb)
    assert agent_amb.last_outcome == AutoSolveOutcome.AMBIGUOUS
    cached_queries = [q for s in steps for q in s.sat_queries if q.cached]
    assert cached_queries
    assert all(q.metrics == SATMetrics() for q in cached_queries)


def test_tc_cache_03_cache_invalidation_when_kb_advances() -> None:
    """TC-CACHE-03: Unknown cell C2 in KB_0 becomes forced CRIMINAL after B1 clue reveals."""
    clue_a1 = Clue(
        "c_A1",
        "A1",
        ClueType.FACT,
        target="B1",
        target_status=Status.INNOCENT,
    )
    state_0 = make_public_state(
        3,
        puzzle_id="cache_inv",
        proved_verdicts={"A1": Status.INNOCENT},
        revealed_clues=(clue_a1,),
    )

    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver(), use_model_cache=True)
    cls_0 = agent.classify_all(state_0)
    assert cls_0["C2"] == Status.UNKNOWN

    # Advance KB_0 -> KB_1 by revealing B1 with clue forcing C2=CRIMINAL
    clue_b1 = Clue(
        "c_B1",
        "B1",
        ClueType.FACT,
        target="C2",
        target_status=Status.CRIMINAL,
    )
    state_1 = make_public_state(
        3,
        puzzle_id="cache_inv",
        step=1,
        proved_verdicts={"A1": Status.INNOCENT, "B1": Status.INNOCENT},
        revealed_clues=(clue_a1, clue_b1),
    )
    cls_1 = agent.classify_all(state_1)
    assert cls_1["C2"] == Status.CRIMINAL


def test_tc_cache_04_isolation_unsat_and_lru_bound() -> None:
    """TC-CACHE-04: UNSAT KB does not poison subsequent valid states; KB LRU <= 8."""
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver(), use_model_cache=True)

    bad_clue = Clue("c_bad", "A1", ClueType.FACT, target="A1", target_status=Status.INNOCENT)
    unsat_state = make_public_state(
        2,
        puzzle_id="p_unsat",
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=(bad_clue,),
    )
    assert agent.check_consistency(unsat_state) is False
    assert agent.classify_all(unsat_state) == {}

    good_clue = Clue("c_good", "A1", ClueType.FACT, target="B1", target_status=Status.CRIMINAL)
    sat_state = make_public_state(
        2,
        puzzle_id="p_sat",
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=(good_clue,),
    )
    assert agent.check_consistency(sat_state) is True
    assert agent.classify_all(sat_state)["B1"] == Status.CRIMINAL

    # Also verify LRU eviction through DeductiveLogicAgent itself
    spy = SpySATSolver(make_solver())
    bounded_agent = DeductiveLogicAgent(StubCNFEncoder(), spy, kb_cache_size=8)
    first_state = make_public_state(2, puzzle_id="evict_0", proved_verdicts={"A1": Status.CRIMINAL})
    bounded_agent.check_consistency(first_state)
    assert spy.call_count == 1
    bounded_agent.check_consistency(first_state)
    assert spy.call_count == 1  # Cache hit

    for idx in range(1, 9):
        st = make_public_state(2, puzzle_id=f"evict_{idx}", proved_verdicts={"A1": Status.CRIMINAL})
        bounded_agent.check_consistency(st)
    # After 8 newer distinct KBs, evict_0 must have been evicted
    calls_before = spy.call_count
    bounded_agent.check_consistency(first_state)
    assert spy.call_count == calls_before + 1

    # Verify KBCache LRU bound <= 8 directly
    cache = KBCache(maxsize=8)
    dummy_cnf = CNFFormula(clauses=(), num_primary_vars=4)
    dummy_stats = CNFStats(num_primary_vars=4, num_aux_vars=0, num_clauses=0, encoding_strategy="stub")
    for idx in range(12):
        st = make_public_state(2, puzzle_id=f"lru_{idx}", proved_verdicts={"A1": Status.CRIMINAL})
        key = make_kb_key(st)
        cache.put(key, KBCacheEntry(consistent=True, cnf=dummy_cnf, cnf_stats=dummy_stats))
    assert len(cache) == 8
    # First 4 entries evicted
    for idx in range(4):
        st = make_public_state(2, puzzle_id=f"lru_{idx}", proved_verdicts={"A1": Status.CRIMINAL})
        assert cache.get(make_kb_key(st)) is None


def test_kb_cache_hit_on_reused_agent_marks_queries_cached() -> None:
    """Reusing one agent (get_hint -> Auto Solve) must not re-log KB-cache hits as real SAT calls."""
    path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(path)

    agent.get_hint(engine.get_public_state())
    calls_after_hint = agent.stats.deduction_sat_calls
    assert calls_after_hint > 0

    steps = agent.run_auto_solve(engine)
    assert agent.last_outcome == AutoSolveOutcome.SOLVED
    assert steps[0].sat_queries
    assert all(q.cached for q in steps[0].sat_queries)
    assert all(q.metrics == SATMetrics() for q in steps[0].sat_queries)

    # Real (uncached) queries logged in the trace equal the SAT calls actually run by auto-solve.
    real_logged = sum(1 for s in steps for q in s.sat_queries if not q.cached)
    assert real_logged == agent.stats.deduction_sat_calls - calls_after_hint


def test_prechecked_consistency_query_is_logged_cached_with_empty_metrics() -> None:
    """check_consistency -> Auto Solve: the reused KB query is cached, not a second real call."""
    path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    agent = DeductiveLogicAgent(StubCNFEncoder(), make_solver())
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(path)

    agent.check_consistency(engine.get_public_state())
    calls_after_check = agent.stats.deduction_sat_calls

    steps = agent.run_auto_solve(engine)
    kb_query = steps[0].sat_queries[0]
    assert kb_query.cell == "KB"
    assert kb_query.cached is True
    assert kb_query.metrics == SATMetrics()
    real_logged = sum(1 for s in steps for q in s.sat_queries if not q.cached)
    assert real_logged == agent.stats.deduction_sat_calls - calls_after_check
