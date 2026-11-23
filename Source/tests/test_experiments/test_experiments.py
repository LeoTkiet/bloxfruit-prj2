"""Fast unit & integration tests for `experiments/` (< 30s total)."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any

import pytest

from experiments.benchmark import (
    PUZZLES_DIR,
    RAW_COLUMNS,
    SUMMARY_COLUMNS,
    build_summary_rows,
    discover_puzzles,
    run_benchmark,
    run_with_timeout,
)
from experiments.configs import (
    get_core_configs,
    get_full_grid_configs,
    select_configs,
)
from experiments.encoder_factory import make_encoder
from experiments.plots import generate_plots
from experiments.uniqueness_report import (
    COLUMNS as UNIQ_COLUMNS,
    generate_uniqueness_report,
)


def _slow_worker_for_timeout_test(
    puzzle_path_str: str,
    cfg: Any,
    result_queue: Any,
) -> None:
    """Top-level spawn-picklable worker simulating a slow solver for timeout test."""
    time.sleep(5.0)
    result_queue.put(("OK", {"terminal_status": "SOLVED"}))


def test_configs_c0_to_c7_and_full_grid() -> None:
    core = get_core_configs()
    assert [c.config_id for c in core] == ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7"]

    by_id = {c.config_id: c for c in core}
    assert (by_id["C0"].encoding, by_id["C0"].heuristic, by_id["C0"].pure_literal, by_id["C0"].model_caching) == ("direct", "lexicographic", False, False)
    assert (by_id["C1"].encoding, by_id["C1"].heuristic, by_id["C1"].pure_literal, by_id["C1"].model_caching) == ("direct", "lexicographic", True, False)
    assert (by_id["C2"].encoding, by_id["C2"].heuristic, by_id["C2"].pure_literal, by_id["C2"].model_caching) == ("direct", "moms", True, False)
    assert (by_id["C3"].encoding, by_id["C3"].heuristic, by_id["C3"].pure_literal, by_id["C3"].model_caching) == ("direct", "jw", True, False)
    assert (by_id["C4"].encoding, by_id["C4"].heuristic, by_id["C4"].pure_literal, by_id["C4"].model_caching) == ("direct", "lexicographic", False, True)
    assert (by_id["C5"].encoding, by_id["C5"].heuristic, by_id["C5"].pure_literal, by_id["C5"].model_caching) == ("sinz", "lexicographic", False, False)
    assert (by_id["C6"].encoding, by_id["C6"].heuristic, by_id["C6"].pure_literal, by_id["C6"].model_caching) == ("direct", "jw", True, True)
    assert (by_id["C7"].encoding, by_id["C7"].heuristic, by_id["C7"].pure_literal, by_id["C7"].model_caching) == ("sinz", "jw", True, True)

    core_moms = {c.config_id: c for c in get_core_configs(best_heur="moms")}
    assert core_moms["C6"].heuristic == "moms"
    assert core_moms["C7"].heuristic == "moms"

    full = get_full_grid_configs()
    assert len(full) == 24
    assert len({(c.encoding, c.heuristic, c.pure_literal, c.model_caching) for c in full}) == 24

    with pytest.raises(ValueError):
        select_configs(["UNKNOWN_CFG"])


def test_discover_puzzles_counts() -> None:
    default_items = discover_puzzles(include_extensions=False)
    assert sum(1 for g, _ in default_items if g == "standard") == 10
    assert sum(1 for g, _ in default_items if g == "edge_case") == 2
    assert sum(1 for g, _ in default_items if g == "extension") == 0

    with_ext = discover_puzzles(include_extensions=True)
    assert sum(1 for g, _ in with_ext if g == "extension") == 3
    assert len(with_ext) == 15


def test_encoder_factory_fallback_and_sinz_skip() -> None:
    with pytest.warns(UserWarning, match="StubCNFEncoder"):
        sel_dir = make_encoder("direct")
    assert sel_dir.is_stub is True
    assert sel_dir.effective_encoding == "stub"
    assert sel_dir.encoder is not None

    sel_sinz = make_encoder("sinz")
    assert sel_sinz.encoder is None
    assert sel_sinz.skipped_reason is not None


def test_small_benchmark_csv_schema_and_cross_config_consistency(tmp_path: Path) -> None:
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    configs = select_configs(["C0", "C4"])

    raw_rows, summary_rows, solved_rates = run_benchmark(
        configs=configs,
        puzzles=[("standard", puzzle_path)],
        repeats=1,
        timeout_s=15.0,
        out_dir=tmp_path,
    )

    assert len(raw_rows) == 2
    assert len(summary_rows) == 2
    assert solved_rates == {"C0": 1.0, "C4": 1.0}

    raw_csv = tmp_path / "benchmark_raw.csv"
    summary_csv = tmp_path / "benchmark_summary.csv"
    assert raw_csv.exists()
    assert summary_csv.exists()
    assert (tmp_path / "env_info.json").exists()

    with raw_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames or ()) == RAW_COLUMNS
        assert len(RAW_COLUMNS) == 31
        loaded_raw = list(reader)
        assert all(r["encoding"] == "stub" for r in loaded_raw)
        assert all(r["terminal_status"] == "SOLVED" for r in loaded_raw)
        assert all(r["reveal_waves"] == "" for r in loaded_raw)

    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames or ()) == SUMMARY_COLUMNS
        loaded_sum = list(reader)
        assert all(r["cross_config_consistency"] == "PASS" for r in loaded_sum)

    # C4 (Model Caching) must perform fewer real SAT calls than C0 (No Cache)
    by_cfg = {r["config_id"]: r for r in loaded_sum}
    assert int(by_cfg["C4"]["sat_calls_total"]) < int(by_cfg["C0"]["sat_calls_total"])
    assert int(by_cfg["C4"]["sat_calls_cached_skipped"]) > 0

    # Charts generate cleanly without crashing even when Sinz (RQ2) is absent
    charts_dir = tmp_path / "charts"
    charts = generate_plots(summary_csv=summary_csv, out_dir=charts_dir)
    chart_names = {p.name for p in charts}
    assert {"rq1_scalability.png", "rq4_model_caching.png"}.issubset(chart_names)
    assert "rq2_direct_vs_sinz.png" not in chart_names


def test_cross_config_consistency_fail_and_single_config_na() -> None:
    base_row = {
        "puzzle_id": "p1",
        "dataset_group": "standard",
        "grid_size": 3,
        "initial_revealed": 1,
        "max_region_size": 3,
        "encoding": "stub",
        "heuristic": "lexicographic",
        "pure_literal": "false",
        "model_caching": "false",
        "terminal_status": "SOLVED",
        "solved_cells": 9,
        "total_cells": 9,
        "primary_vars": 9,
        "aux_vars_final": 0,
        "aux_vars_max": 0,
        "cnf_clauses_final": 10,
        "cnf_clauses_avg": 5.0,
        "sat_calls_total": 10,
        "sat_calls_cached_skipped": 0,
        "total_decisions": 1,
        "total_propagations": 5,
        "total_backtracks": 0,
        "deduction_steps": 1,
        "solver_runtime_ms": 1.0,
        "total_runtime_ms": 2.0,
        "repeat_idx": 1,
    }
    # Single config -> NA (never false PASS)
    single_sum = build_summary_rows(
        [{**base_row, "config_id": "C0"}],
        {("p1", "C0", 1): ((1, "B1", "CRIMINAL", "ACCEPTED"),)},
    )
    assert single_sum[0]["cross_config_consistency"] == "NA"

    # Two configs with mismatched verdict traces -> FAIL
    r0 = {**base_row, "config_id": "C0"}
    r4 = {**base_row, "config_id": "C4", "model_caching": "true"}
    mismatch_sum = build_summary_rows(
        [r0, r4],
        {
            ("p1", "C0", 1): ((1, "B1", "CRIMINAL", "ACCEPTED"),),
            ("p1", "C4", 1): ((1, "B1", "INNOCENT", "ACCEPTED"),),
        },
    )
    assert all(r["cross_config_consistency"] == "FAIL" for r in mismatch_sum)

    # Missing trace entries must NOT silently match as empty tuples -> FAIL
    missing_trace_sum = build_summary_rows([r0, r4], {})
    assert all(r["cross_config_consistency"] == "FAIL" for r in missing_trace_sum)


def test_sinz_config_records_skipped_no_encoder(tmp_path: Path) -> None:
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    configs = select_configs(["C5"])
    raw_rows, summary_rows, _ = run_benchmark(
        configs=configs,
        puzzles=[("standard", puzzle_path)],
        repeats=1,
        timeout_s=10.0,
        out_dir=tmp_path,
    )
    assert len(raw_rows) == 1
    assert raw_rows[0]["terminal_status"] == "SKIPPED_NO_ENCODER"
    assert raw_rows[0]["encoding"] == "sinz"
    assert summary_rows[0]["terminal_status"] == "SKIPPED_NO_ENCODER"
    assert summary_rows[0]["cross_config_consistency"] == "NA"


def test_windows_multiprocessing_timeout_returns_timeout() -> None:
    puzzle_path = PUZZLES_DIR / "3x3" / "3x3_01_precinct_basics.json"
    cfg = select_configs(["C0"])[0]
    res = run_with_timeout(
        puzzle_path,
        cfg,
        timeout_s=0.25,
        worker_target=_slow_worker_for_timeout_test,
    )
    assert res["terminal_status"] == "TIMEOUT"
    assert "Timed out" in res["error_message"]


def test_uniqueness_report_all_15_puzzles(tmp_path: Path) -> None:
    out_csv = tmp_path / "uniqueness_report.csv"
    rows = generate_uniqueness_report(out_csv=out_csv)
    assert len(rows) == 15
    assert out_csv.exists()

    with out_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames or ()) == UNIQ_COLUMNS
        loaded = list(reader)
        assert len(loaded) == 15

    by_id = {r["puzzle_id"]: r for r in rows}
    std_ext = [r for r in rows if r["group"] in ("standard", "extension")]
    assert len(std_ext) == 13
    assert all(r["status"] == "UNIQUE" and r["matches_hidden_solution"] == "true" for r in std_ext)
    assert by_id["edge_3x3_inconsistent"]["status"] == "UNSAT"
