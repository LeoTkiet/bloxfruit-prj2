"""Headless benchmark runner producing `benchmark_raw.csv` and `benchmark_summary.csv`.

Notes on nullable columns:
- `reveal_waves` is intentionally left blank (`""`) per official FAQ #12.
- When a run ends with `SKIPPED_NO_ENCODER`, `TIMEOUT`, or `ERROR`, solver/CNF
  columns that were not produced are left blank (`""`).
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import multiprocessing
import os
import pickle
import platform
import queue
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence

SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from agent import AutoSolveOutcome, DeductiveLogicAgent  # noqa: E402
from core.contracts.models import Clue, VerdictCode  # noqa: E402
from engine.game_engine import GameEngine  # noqa: E402
from engine.puzzle_loader import load_puzzle_definition  # noqa: E402
from engine.puzzle_validator import resolve_region_cells  # noqa: E402
from experiments.configs import ExperimentConfig, select_configs  # noqa: E402
from experiments.encoder_factory import EncoderSelection, make_encoder  # noqa: E402
from experiments.solver_factory import make_solver  # noqa: E402

PUZZLES_DIR = SOURCE_DIR / "puzzles"
DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"

RAW_COLUMNS: tuple[str, ...] = (
    "run_timestamp",
    "puzzle_id",
    "dataset_group",
    "grid_size",
    "initial_revealed",
    "max_region_size",
    "config_id",
    "encoding",
    "heuristic",
    "pure_literal",
    "model_caching",
    "repeat_idx",
    "timeout_limit_ms",
    "terminal_status",
    "solved_cells",
    "total_cells",
    "primary_vars",
    "aux_vars_final",
    "aux_vars_max",
    "cnf_clauses_final",
    "cnf_clauses_avg",
    "sat_calls_total",
    "sat_calls_cached_skipped",
    "total_decisions",
    "total_propagations",
    "total_backtracks",
    "deduction_steps",
    "reveal_waves",
    "solver_runtime_ms",
    "total_runtime_ms",
    "error_message",
)

SUMMARY_COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "dataset_group",
    "grid_size",
    "initial_revealed",
    "max_region_size",
    "config_id",
    "encoding",
    "heuristic",
    "pure_literal",
    "model_caching",
    "terminal_status",
    "solved_cells",
    "total_cells",
    "primary_vars",
    "aux_vars_final",
    "aux_vars_max",
    "cnf_clauses_final",
    "cnf_clauses_avg",
    "sat_calls_total",
    "sat_calls_cached_skipped",
    "total_decisions",
    "total_propagations",
    "total_backtracks",
    "deduction_steps",
    "reveal_waves",
    "repeats",
    "deterministic_check",
    "cross_config_consistency",
    "solver_runtime_ms_median",
    "solver_runtime_ms_mean",
    "solver_runtime_ms_std",
    "total_runtime_ms_median",
    "total_runtime_ms_mean",
    "total_runtime_ms_std",
)


def discover_puzzles(
    puzzles_dir: Path = PUZZLES_DIR,
    *,
    include_extensions: bool = False,
) -> list[tuple[str, Path]]:
    """Return `(dataset_group, path)` for the 10 standard + 2 edge_cases (+ extensions)."""
    items: list[tuple[str, Path]] = []
    for sub in ("3x3", "4x4", "5x5"):
        for p in sorted((puzzles_dir / sub).glob("*.json")):
            items.append(("standard", p))
    if include_extensions:
        for p in sorted((puzzles_dir / "extensions").glob("*.json")):
            items.append(("extension", p))
    for p in sorted((puzzles_dir / "edge_cases").glob("*.json")):
        items.append(("edge_case", p))
    return items


def _compute_max_region_size(clues: Sequence[Clue], grid_size: int) -> int:
    max_size = 0
    for clue in clues:
        if clue.region is not None:
            max_size = max(max_size, len(resolve_region_cells(clue.region, grid_size)))
        if clue.region_b is not None:
            max_size = max(max_size, len(resolve_region_cells(clue.region_b, grid_size)))
    return max_size


# Errors `multiprocessing.Queue.get` can raise when the worker dies mid-write.
_QUEUE_READ_ERRORS = (EOFError, OSError, pickle.UnpicklingError)


def _puzzle_max_region_size(puzzle: Any) -> int | str:
    """Puzzle-level `max_region_size` over all clues, identical for every config/status.

    Counts every clue that has a region (incl. PARITY / COMPARE_COUNTS). Returns `""`
    when a region is invalid so an unvalidated puzzle yields an ERROR row in its worker
    instead of aborting the whole benchmark in the parent process.
    """
    try:
        return _compute_max_region_size(
            [ch.hidden_clue for ch in puzzle.characters], puzzle.grid_size
        )
    except ValueError:  # PuzzleValidationError subclasses ValueError
        return ""


def _execute_single_in_process(
    puzzle_path_str: str,
    cfg: ExperimentConfig,
) -> dict[str, Any]:
    """Run one `(puzzle, config)` trial in the current process and return raw metrics."""
    puzzle_path = Path(puzzle_path_str)
    puzzle = load_puzzle_definition(puzzle_path)
    sel = make_encoder(cfg.encoding)
    if sel.encoder is None:
        return {
            "terminal_status": "SKIPPED_NO_ENCODER",
            "effective_encoding": sel.effective_encoding,
            "error_message": sel.skipped_reason or "Missing encoder",
            "max_region_size": _puzzle_max_region_size(puzzle),
            "verdict_trace": (),
        }

    solver = make_solver(heuristic=cfg.heuristic, pure_literal=cfg.pure_literal)
    agent = DeductiveLogicAgent(
        sel.encoder,
        solver,
        use_model_cache=cfg.model_caching,
    )
    engine = GameEngine(logic_agent=agent)
    engine.load_puzzle(puzzle_path)

    gc.collect()
    t0 = time.perf_counter()
    steps = agent.run_auto_solve(engine)
    total_runtime_ms = (time.perf_counter() - t0) * 1000.0
    final_state = engine.get_public_state()

    outcome = agent.last_outcome or AutoSolveOutcome.AMBIGUOUS
    terminal_status = outcome.value

    cnf_stats_list = [s.cnf_stats for s in steps if s.cnf_stats is not None]
    aux_final = cnf_stats_list[-1].num_aux_vars if cnf_stats_list else 0
    aux_max = max((c.num_aux_vars for c in cnf_stats_list), default=0)
    clauses_final = cnf_stats_list[-1].num_clauses if cnf_stats_list else 0
    clauses_avg = (
        round(sum(c.num_clauses for c in cnf_stats_list) / len(cnf_stats_list), 2)
        if cnf_stats_list
        else 0.0
    )

    real_queries = [q for s in steps for q in s.sat_queries if not q.cached]
    cached_queries = [q for s in steps for q in s.sat_queries if q.cached]

    sat_calls_total = len(real_queries)
    sat_calls_cached_skipped = len(cached_queries)
    total_decisions = sum(q.metrics.decisions for q in real_queries)
    total_propagations = sum(q.metrics.propagations for q in real_queries)
    total_backtracks = sum(q.metrics.backtracks for q in real_queries)
    solver_runtime_ms = round(sum(q.metrics.runtime_ms for q in real_queries), 3)
    deduction_steps = sum(1 for s in steps if s.verdict_code == VerdictCode.ACCEPTED)
    max_region_size = _puzzle_max_region_size(puzzle)

    error_msg = ""
    if terminal_status == "AMBIGUOUS":
        error_msg = f"Stopped at step {final_state.step} with no forced cell"
    elif terminal_status == "INCONSISTENT":
        error_msg = f"KB_t UNSAT at step {final_state.step}"

    verdict_trace = tuple(
        (s.step_number, s.cell, s.verdict.value, s.verdict_code.value) for s in steps
    )

    return {
        "effective_encoding": sel.effective_encoding,
        "max_region_size": max_region_size,
        "terminal_status": terminal_status,
        "solved_cells": len(final_state.proved_verdicts),
        "total_cells": puzzle.grid_size * puzzle.grid_size,
        "primary_vars": puzzle.grid_size * puzzle.grid_size,
        "aux_vars_final": aux_final,
        "aux_vars_max": aux_max,
        "cnf_clauses_final": clauses_final,
        "cnf_clauses_avg": clauses_avg,
        "sat_calls_total": sat_calls_total,
        "sat_calls_cached_skipped": sat_calls_cached_skipped,
        "total_decisions": total_decisions,
        "total_propagations": total_propagations,
        "total_backtracks": total_backtracks,
        "deduction_steps": deduction_steps,
        "solver_runtime_ms": solver_runtime_ms,
        "total_runtime_ms": round(total_runtime_ms, 3),
        "error_message": error_msg,
        "verdict_trace": verdict_trace,
    }


def _worker_entrypoint(
    puzzle_path_str: str,
    cfg: ExperimentConfig,
    result_queue: Any,
) -> None:
    """Spawn-safe multiprocessing entrypoint for Windows timeout isolation."""
    try:
        payload = _execute_single_in_process(puzzle_path_str, cfg)
        result_queue.put(("OK", payload))
    except Exception as exc:  # pragma: no cover - defensive worker guard
        result_queue.put(("ERROR", f"{type(exc).__name__}: {exc}"))


def run_with_timeout(
    puzzle_path: Path,
    cfg: ExperimentConfig,
    timeout_s: float,
    *,
    worker_target: Any = _worker_entrypoint,
) -> dict[str, Any]:
    """Run one `(puzzle, config)` trial in an isolated spawn process with timeout."""
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()

    prev_pythonpath = os.environ.get("PYTHONPATH")
    source_str = str(SOURCE_DIR)
    if prev_pythonpath:
        if source_str not in prev_pythonpath.split(os.pathsep):
            os.environ["PYTHONPATH"] = f"{source_str}{os.pathsep}{prev_pythonpath}"
    else:
        os.environ["PYTHONPATH"] = source_str

    proc = ctx.Process(
        target=worker_target,
        args=(str(puzzle_path), cfg, q),
    )
    try:
        proc.start()
    finally:
        if prev_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = prev_pythonpath

    deadline = time.monotonic() + max(timeout_s, 0.01)
    status_payload: Optional[tuple[str, Any]] = None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            status_payload = q.get(timeout=min(0.05, remaining))
            break
        except queue.Empty:
            if not proc.is_alive():
                try:
                    status_payload = q.get(timeout=0.1)
                except queue.Empty:
                    status_payload = None
                except _QUEUE_READ_ERRORS as exc:
                    status_payload = ("ERROR", f"Worker queue failed: {type(exc).__name__}: {exc}")
                break
        except _QUEUE_READ_ERRORS as exc:
            # Broken pipe / truncated payload from a dying worker: report ERROR, keep cleanup.
            status_payload = ("ERROR", f"Worker queue failed: {type(exc).__name__}: {exc}")
            break

    if status_payload is None:
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            if proc.is_alive():  # pragma: no cover
                proc.kill()
                proc.join(timeout=2)
            q.close()
            return {
                "terminal_status": "TIMEOUT",
                "total_runtime_ms": round(timeout_s * 1000.0, 3),
                "error_message": f"Timed out after {timeout_s}s",
                "verdict_trace": (),
            }
        proc.join(timeout=2)
        q.close()
        return {
            "terminal_status": "ERROR",
            "error_message": f"Worker exited with code {proc.exitcode} without payload",
            "verdict_trace": (),
        }

    proc.join(timeout=2)
    if proc.is_alive():  # pragma: no cover
        proc.terminate()
        proc.join(timeout=2)
    q.close()

    kind, data = status_payload
    if kind == "ERROR":
        return {
            "terminal_status": "ERROR",
            "error_message": str(data),
            "verdict_trace": (),
        }
    return data


def _build_raw_row(
    *,
    puzzle_id: str,
    dataset_group: str,
    grid_size: int,
    initial_revealed: int,
    cfg: ExperimentConfig,
    effective_encoding: str,
    repeat_idx: int,
    timeout_limit_ms: int,
    result: dict[str, Any],
    max_region_size: Optional[int | str] = None,
) -> dict[str, Any]:
    total_cells = grid_size * grid_size
    if max_region_size is None:
        max_region_size = result.get("max_region_size", "")
    return {
        "run_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "puzzle_id": puzzle_id,
        "dataset_group": dataset_group,
        "grid_size": grid_size,
        "initial_revealed": initial_revealed,
        "max_region_size": max_region_size,
        "config_id": cfg.config_id,
        "encoding": result.get("effective_encoding", effective_encoding),
        "heuristic": cfg.heuristic,
        "pure_literal": str(cfg.pure_literal).lower(),
        "model_caching": str(cfg.model_caching).lower(),
        "repeat_idx": repeat_idx,
        "timeout_limit_ms": timeout_limit_ms,
        "terminal_status": result["terminal_status"],
        "solved_cells": result.get("solved_cells", ""),
        "total_cells": total_cells,
        "primary_vars": total_cells,
        "aux_vars_final": result.get("aux_vars_final", ""),
        "aux_vars_max": result.get("aux_vars_max", ""),
        "cnf_clauses_final": result.get("cnf_clauses_final", ""),
        "cnf_clauses_avg": result.get("cnf_clauses_avg", ""),
        "sat_calls_total": result.get("sat_calls_total", ""),
        "sat_calls_cached_skipped": result.get("sat_calls_cached_skipped", ""),
        "total_decisions": result.get("total_decisions", ""),
        "total_propagations": result.get("total_propagations", ""),
        "total_backtracks": result.get("total_backtracks", ""),
        "deduction_steps": result.get("deduction_steps", ""),
        "reveal_waves": "",  # Intentionally skipped per FAQ #12
        "solver_runtime_ms": result.get("solver_runtime_ms", ""),
        "total_runtime_ms": result.get("total_runtime_ms", ""),
        "error_message": result.get("error_message", ""),
    }


def _runtime_stats(values: list[float]) -> tuple[Any, Any, Any]:
    if not values:
        return "", "", ""
    med = round(statistics.median(values), 3)
    mean = round(statistics.mean(values), 3)
    std = round(statistics.stdev(values), 3) if len(values) > 1 else 0.0
    return med, mean, std


def build_summary_rows(
    raw_rows: Sequence[dict[str, Any]],
    traces_by_run: dict[tuple[str, str, int], tuple[Any, ...]],
) -> list[dict[str, Any]]:
    """Aggregate raw rows into `benchmark_summary.csv` with deterministic and cross-config checks."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in raw_rows:
        key = (row["puzzle_id"], row["config_id"])
        grouped.setdefault(key, []).append(row)

    # First compute per-(puzzle_id, config_id) signature for cross-config comparison
    valid_statuses = {"SOLVED", "AMBIGUOUS", "INCONSISTENT"}
    signatures_by_puzzle: dict[str, dict[str, tuple[Any, ...]]] = {}
    det_checks: dict[tuple[str, str], str] = {}

    for (pid, cid), rows in grouped.items():
        all_valid = all(r["terminal_status"] in valid_statuses for r in rows)
        if not all_valid or len(rows) < 2:
            det_checks[(pid, cid)] = "NA"
        else:
            det_sigs = {
                (
                    r["terminal_status"],
                    r["primary_vars"],
                    r["aux_vars_final"],
                    r["aux_vars_max"],
                    r["cnf_clauses_final"],
                    r["sat_calls_total"],
                    r["total_decisions"],
                    r["total_propagations"],
                    r["total_backtracks"],
                    r["deduction_steps"],
                    traces_by_run.get(
                        (pid, cid, int(r["repeat_idx"])),
                        ("__MISSING_TRACE__", pid, cid, int(r["repeat_idx"])),
                    ),
                )
                for r in rows
            }
            det_checks[(pid, cid)] = "PASS" if len(det_sigs) == 1 else "FAIL"

        if all_valid:
            cfg_sigs = {
                (
                    r["terminal_status"],
                    r["deduction_steps"],
                    traces_by_run.get(
                        (pid, cid, int(r["repeat_idx"])),
                        ("__MISSING_TRACE__", pid, cid, int(r["repeat_idx"])),
                    ),
                )
                for r in rows
            }
            if len(cfg_sigs) == 1:
                signatures_by_puzzle.setdefault(pid, {})[cid] = next(iter(cfg_sigs))
            else:
                signatures_by_puzzle.setdefault(pid, {})[cid] = ("__MISMATCH__", cid)

    cross_checks: dict[tuple[str, str], str] = {}
    for pid, cfg_sigs in signatures_by_puzzle.items():
        if len(cfg_sigs) < 2:
            for cid in cfg_sigs:
                cross_checks[(pid, cid)] = "NA"
        else:
            unique_sigs = set(cfg_sigs.values())
            has_internal_err = any(sig[0] == "__MISMATCH__" for sig in unique_sigs)
            verdict = "PASS" if (not has_internal_err and len(unique_sigs) == 1) else "FAIL"
            for cid in cfg_sigs:
                cross_checks[(pid, cid)] = verdict

    summary: list[dict[str, Any]] = []
    for (pid, cid), rows in grouped.items():
        first = rows[0]
        solver_rts = [
            float(r["solver_runtime_ms"])
            for r in rows
            if r["solver_runtime_ms"] != ""
        ]
        total_rts = [
            float(r["total_runtime_ms"])
            for r in rows
            if r["total_runtime_ms"] != ""
        ]
        s_med, s_mean, s_std = _runtime_stats(solver_rts)
        t_med, t_mean, t_std = _runtime_stats(total_rts)

        summary.append(
            {
                "puzzle_id": pid,
                "dataset_group": first["dataset_group"],
                "grid_size": first["grid_size"],
                "initial_revealed": first["initial_revealed"],
                "max_region_size": first["max_region_size"],
                "config_id": cid,
                "encoding": first["encoding"],
                "heuristic": first["heuristic"],
                "pure_literal": first["pure_literal"],
                "model_caching": first["model_caching"],
                "terminal_status": first["terminal_status"],
                "solved_cells": first["solved_cells"],
                "total_cells": first["total_cells"],
                "primary_vars": first["primary_vars"],
                "aux_vars_final": first["aux_vars_final"],
                "aux_vars_max": first["aux_vars_max"],
                "cnf_clauses_final": first["cnf_clauses_final"],
                "cnf_clauses_avg": first["cnf_clauses_avg"],
                "sat_calls_total": first["sat_calls_total"],
                "sat_calls_cached_skipped": first["sat_calls_cached_skipped"],
                "total_decisions": first["total_decisions"],
                "total_propagations": first["total_propagations"],
                "total_backtracks": first["total_backtracks"],
                "deduction_steps": first["deduction_steps"],
                "reveal_waves": "",
                "repeats": len(rows),
                "deterministic_check": det_checks.get((pid, cid), "NA"),
                "cross_config_consistency": cross_checks.get((pid, cid), "NA"),
                "solver_runtime_ms_median": s_med,
                "solver_runtime_ms_mean": s_mean,
                "solver_runtime_ms_std": s_std,
                "total_runtime_ms_median": t_med,
                "total_runtime_ms_mean": t_mean,
                "total_runtime_ms_std": t_std,
            }
        )
    return summary


def compute_solved_rates(
    summary_rows: Sequence[dict[str, Any]],
    *,
    dataset_group: str = "standard",
) -> dict[str, float]:
    """Compute per-config SOLVED fraction over puzzles in `dataset_group`."""
    counts: dict[str, list[int]] = {}
    for row in summary_rows:
        if row["dataset_group"] != dataset_group:
            continue
        cid = str(row["config_id"])
        bucket = counts.setdefault(cid, [0, 0])
        bucket[1] += 1
        if row["terminal_status"] == "SOLVED":
            bucket[0] += 1
    return {
        cid: round(solved / total, 4) if total else 0.0
        for cid, (solved, total) in counts.items()
    }


def _collect_env_info() -> dict[str, Any]:
    git_hash = ""
    try:
        git_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=SOURCE_DIR.parent,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        )
    except Exception:
        git_hash = ""
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "os": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python_version": sys.version,
        "git_commit": git_hash,
    }


def run_benchmark(
    *,
    configs: Sequence[ExperimentConfig],
    puzzles: Sequence[tuple[str, Path]],
    repeats: int = 1,
    timeout_s: float = 60.0,
    out_dir: Path = DEFAULT_RESULTS_DIR,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    """Run all `(puzzle, config, repeat)` trials and write CSV + env_info outputs."""
    if repeats < 1:
        raise ValueError(f"repeats must be >= 1, got {repeats}")

    out_dir.mkdir(parents=True, exist_ok=True)
    timeout_limit_ms = int(round(timeout_s * 1000))

    # Cache EncoderSelection per strategy so missing-encoder warnings emit cleanly once per strategy
    selections: dict[str, EncoderSelection] = {}
    for cfg in configs:
        if cfg.encoding not in selections:
            selections[cfg.encoding] = make_encoder(cfg.encoding)

    raw_rows: list[dict[str, Any]] = []
    traces_by_run: dict[tuple[str, str, int], tuple[Any, ...]] = {}

    for dataset_group, puzzle_path in puzzles:
        puzzle = load_puzzle_definition(puzzle_path)
        puzzle_max_region = _puzzle_max_region_size(puzzle)

        for cfg in configs:
            sel = selections[cfg.encoding]
            if sel.encoder is None:
                raw_rows.append(
                    _build_raw_row(
                        puzzle_id=puzzle.puzzle_id,
                        dataset_group=dataset_group,
                        grid_size=puzzle.grid_size,
                        initial_revealed=len(puzzle.initial_revealed),
                        cfg=cfg,
                        effective_encoding=sel.effective_encoding,
                        repeat_idx=1,
                        timeout_limit_ms=timeout_limit_ms,
                        max_region_size=puzzle_max_region,
                        result={
                            "terminal_status": "SKIPPED_NO_ENCODER",
                            "effective_encoding": sel.effective_encoding,
                            "error_message": sel.skipped_reason or "Missing encoder",
                        },
                    )
                )
                continue

            for rep in range(1, repeats + 1):
                res = run_with_timeout(puzzle_path, cfg, timeout_s=timeout_s)
                traces_by_run[(puzzle.puzzle_id, cfg.config_id, rep)] = tuple(
                    res.get("verdict_trace", ())
                )
                raw_rows.append(
                    _build_raw_row(
                        puzzle_id=puzzle.puzzle_id,
                        dataset_group=dataset_group,
                        grid_size=puzzle.grid_size,
                        initial_revealed=len(puzzle.initial_revealed),
                        cfg=cfg,
                        effective_encoding=sel.effective_encoding,
                        repeat_idx=rep,
                        timeout_limit_ms=timeout_limit_ms,
                        max_region_size=puzzle_max_region,
                        result=res,
                    )
                )
                if res["terminal_status"] == "TIMEOUT" and rep == 1:
                    break

    summary_rows = build_summary_rows(raw_rows, traces_by_run)
    solved_rates = compute_solved_rates(summary_rows, dataset_group="standard")

    raw_path = out_dir / "benchmark_raw.csv"
    with raw_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(RAW_COLUMNS))
        writer.writeheader()
        writer.writerows(raw_rows)

    summary_path = out_dir / "benchmark_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(SUMMARY_COLUMNS))
        writer.writeheader()
        writer.writerows(summary_rows)

    env_info = _collect_env_info()
    env_info["solved_rate_standard"] = solved_rates
    (out_dir / "env_info.json").write_text(
        json.dumps(env_info, indent=2), encoding="utf-8"
    )

    return raw_rows, summary_rows, solved_rates


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Griductive Solver headless benchmark."
    )
    parser.add_argument(
        "--configs",
        type=str,
        default=None,
        help="Comma-separated config IDs (e.g. C0,C4). Default: all C0-C7.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of measured repeats per (puzzle, config). Default: 1.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=60.0,
        help="Per-run timeout in seconds. Default: 60.0.",
    )
    parser.add_argument(
        "--include-extensions",
        action="store_true",
        help="Include Source/puzzles/extensions/*.json in addition to standard + edge_cases.",
    )
    parser.add_argument(
        "--full-grid",
        action="store_true",
        help="Run all 24 factorial config combinations instead of C0-C7.",
    )
    parser.add_argument(
        "--best-heur",
        type=str,
        default="jw",
        choices=("lexicographic", "moms", "jw"),
        help="Heuristic used for C6 and C7. Default: jw.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Output directory for CSVs and env_info.json.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    config_ids = args.configs.split(",") if args.configs else None
    configs = select_configs(
        config_ids, best_heur=args.best_heur, full_grid=args.full_grid
    )
    puzzles = discover_puzzles(include_extensions=args.include_extensions)

    t0 = time.perf_counter()
    raw_rows, summary_rows, solved_rates = run_benchmark(
        configs=configs,
        puzzles=puzzles,
        repeats=args.repeats,
        timeout_s=args.timeout_s,
        out_dir=args.out,
    )
    elapsed_s = time.perf_counter() - t0
    print(
        f"Benchmark finished in {elapsed_s:.2f}s: "
        f"{len(raw_rows)} raw rows, {len(summary_rows)} summary rows -> {args.out}"
    )
    print(f"Standard solved_rate by config: {solved_rates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
