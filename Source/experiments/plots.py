"""Generate RQ1-RQ4 PNG charts from `benchmark_summary.csv` (headless matplotlib)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_SUMMARY_CSV = DEFAULT_RESULTS_DIR / "benchmark_summary.csv"
DEFAULT_CHARTS_DIR = DEFAULT_RESULTS_DIR / "charts"

_VALID_STATUSES = {"SOLVED", "AMBIGUOUS", "INCONSISTENT"}


def _load_summary(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _to_float(val: Any) -> Optional[float]:
    if val in (None, ""):
        return None
    return float(val)


def _plot_rq1_scalability(
    rows: Sequence[dict[str, Any]],
    out_dir: Path,
) -> Optional[Path]:
    std = [
        r
        for r in rows
        if r["dataset_group"] == "standard" and r["terminal_status"] in _VALID_STATUSES
    ]
    if not std:
        print("[RQ1] Skipped: no valid standard rows.")
        return None

    sizes = sorted({int(r["grid_size"]) for r in std})
    configs = sorted({r["config_id"] for r in std})

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)
    for cid in configs:
        rt_vals = []
        sat_vals = []
        valid_sizes = []
        for sz in sizes:
            sub = [r for r in std if r["config_id"] == cid and int(r["grid_size"]) == sz]
            rts = [_to_float(r["total_runtime_ms_median"]) for r in sub]
            sats = [_to_float(r["sat_calls_total"]) for r in sub]
            rts_clean = [x for x in rts if x is not None]
            sats_clean = [x for x in sats if x is not None]
            if rts_clean and sats_clean:
                valid_sizes.append(f"{sz}x{sz}")
                rt_vals.append(sum(rts_clean) / len(rts_clean))
                sat_vals.append(sum(sats_clean) / len(sats_clean))
        if valid_sizes:
            ax1.plot(valid_sizes, rt_vals, marker="o", label=cid)
            ax2.plot(valid_sizes, sat_vals, marker="s", label=cid)

    ax1.set_title("RQ1: Mean Median Runtime by Grid Size")
    ax1.set_xlabel("Grid Size")
    ax1.set_ylabel("Total Runtime (ms)")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8)

    ax2.set_title("RQ1: Mean SAT Calls by Grid Size")
    ax2.set_xlabel("Grid Size")
    ax2.set_ylabel("SAT Calls (non-cached)")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(fontsize=8)

    fig.tight_layout()
    out_path = out_dir / "rq1_scalability.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def _plot_rq2_direct_vs_sinz(
    rows: Sequence[dict[str, Any]],
    out_dir: Path,
) -> Optional[Path]:
    std = [
        r
        for r in rows
        if r["dataset_group"] == "standard" and r["terminal_status"] in _VALID_STATUSES
    ]
    direct_rows = [r for r in std if r["config_id"] == "C0"]
    sinz_rows = [r for r in std if r["config_id"] == "C5"]
    if not direct_rows or not sinz_rows:
        print(
            "[RQ2] Skipped rq2_direct_vs_sinz.png: Sinz (C5) data not available "
            "(waiting for TV2 real encoder)."
        )
        return None

    sinz_by_pid = {r["puzzle_id"]: r for r in sinz_rows}
    paired = [
        (r, sinz_by_pid[r["puzzle_id"]])
        for r in direct_rows
        if r["puzzle_id"] in sinz_by_pid
    ]
    if not paired:
        print("[RQ2] Skipped rq2_direct_vs_sinz.png: no matching puzzle pairs.")
        return None

    pids = [p[0]["puzzle_id"] for p in paired]
    clauses_d = [float(p[0]["cnf_clauses_final"]) for p in paired]
    clauses_s = [float(p[1]["cnf_clauses_final"]) for p in paired]
    aux_d = [float(p[0]["aux_vars_final"]) for p in paired]
    aux_s = [float(p[1]["aux_vars_final"]) for p in paired]

    x = list(range(len(pids)))
    w = 0.36
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)

    ax1.bar([i - w / 2 for i in x], aux_d, width=w, label="Direct/C0")
    ax1.bar([i + w / 2 for i in x], aux_s, width=w, label="Sinz/C5")
    ax1.set_xticks(x)
    ax1.set_xticklabels(pids, rotation=30, ha="right", fontsize=8)
    ax1.set_title("RQ2: Final Aux Vars (Direct vs Sinz)")
    ax1.set_ylabel("Aux Vars")
    ax1.legend()

    ax2.bar([i - w / 2 for i in x], clauses_d, width=w, label="Direct/C0")
    ax2.bar([i + w / 2 for i in x], clauses_s, width=w, label="Sinz/C5")
    ax2.set_xticks(x)
    ax2.set_xticklabels(pids, rotation=30, ha="right", fontsize=8)
    ax2.set_title("RQ2: Final CNF Clauses (Direct vs Sinz)")
    ax2.set_ylabel("CNF Clauses")
    ax2.legend()

    fig.tight_layout()
    out_path = out_dir / "rq2_direct_vs_sinz.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def _plot_rq3_heuristics(
    rows: Sequence[dict[str, Any]],
    out_dir: Path,
) -> Optional[Path]:
    target_cfgs = ["C0", "C1", "C2", "C3"]
    std = [
        r
        for r in rows
        if r["dataset_group"] == "standard"
        and r["terminal_status"] in _VALID_STATUSES
        and r["config_id"] in target_cfgs
    ]
    present = [c for c in target_cfgs if any(r["config_id"] == c for r in std)]
    if not present:
        print("[RQ3] Skipped: no heuristic comparison rows (C0-C3).")
        return None

    decisions = [
        sum(float(r["total_decisions"]) for r in std if r["config_id"] == c)
        for c in present
    ]
    backtracks = [
        sum(float(r["total_backtracks"]) for r in std if r["config_id"] == c)
        for c in present
    ]

    x = list(range(len(present)))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=300)
    ax1.bar(x, decisions, color="#2a6f97")
    ax1.set_xticks(x)
    ax1.set_xticklabels(present)
    ax1.set_title("RQ3: Total Decisions by Config")
    ax1.set_ylabel("Decisions")

    ax2.bar(x, backtracks, color="#c8553d")
    ax2.set_xticks(x)
    ax2.set_xticklabels(present)
    ax2.set_title("RQ3: Total Backtracks by Config")
    ax2.set_ylabel("Backtracks")

    fig.tight_layout()
    out_path = out_dir / "rq3_heuristics.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def _plot_rq4_model_caching(
    rows: Sequence[dict[str, Any]],
    out_dir: Path,
) -> Optional[Path]:
    std = [
        r
        for r in rows
        if r["dataset_group"] == "standard" and r["terminal_status"] in _VALID_STATUSES
    ]
    c0 = {r["puzzle_id"]: r for r in std if r["config_id"] == "C0"}
    c4 = {r["puzzle_id"]: r for r in std if r["config_id"] == "C4"}
    common = sorted(set(c0.keys()) & set(c4.keys()))
    if not common:
        print("[RQ4] Skipped: need both C0 and C4 standard rows.")
        return None

    calls_c0 = [float(c0[pid]["sat_calls_total"]) for pid in common]
    calls_c4 = [float(c4[pid]["sat_calls_total"]) for pid in common]

    x = list(range(len(common)))
    w = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    ax.bar([i - w / 2 for i in x], calls_c0, width=w, label="C0 (No Cache)")
    ax.bar([i + w / 2 for i in x], calls_c4, width=w, label="C4 (Model Cache)")
    ax.set_xticks(x)
    ax.set_xticklabels(common, rotation=30, ha="right", fontsize=8)
    ax.set_title("RQ4: SAT Calls With vs Without Model Caching")
    ax.set_ylabel("SAT Calls (non-cached)")
    ax.legend()

    fig.tight_layout()
    out_path = out_dir / "rq4_model_caching.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def generate_plots(
    summary_csv: Path = DEFAULT_SUMMARY_CSV,
    out_dir: Path = DEFAULT_CHARTS_DIR,
) -> list[Path]:
    """Generate all available RQ charts from `summary_csv` into `out_dir`."""
    rows = _load_summary(summary_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for fn in (
        _plot_rq1_scalability,
        _plot_rq2_direct_vs_sinz,
        _plot_rq3_heuristics,
        _plot_rq4_model_caching,
    ):
        p = fn(rows, out_dir)
        if p is not None:
            generated.append(p)
    return generated


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Plot Griductive benchmark charts.")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_CHARTS_DIR)
    args = parser.parse_args(argv)
    paths = generate_plots(summary_csv=args.summary, out_dir=args.out)
    print(f"Generated {len(paths)} chart(s): {[p.name for p in paths]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
