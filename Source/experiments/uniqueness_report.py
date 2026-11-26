"""Run `check_uniqueness` across all 15 puzzles and export `uniqueness_report.csv`."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any, Optional, Sequence

SOURCE_DIR = Path(__file__).resolve().parents[1]
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from agent import check_uniqueness  # noqa: E402
from engine.game_engine import GameEngine  # noqa: E402
from engine.puzzle_loader import load_puzzle_definition  # noqa: E402
from experiments.encoder_factory import make_encoder  # noqa: E402
from experiments.solver_factory import make_solver  # noqa: E402

PUZZLES_DIR = SOURCE_DIR / "puzzles"
DEFAULT_OUTPUT_CSV = Path(__file__).resolve().parent / "results" / "uniqueness_report.csv"

COLUMNS: tuple[str, ...] = (
    "puzzle_id",
    "group",
    "grid_size",
    "encoding",
    "status",
    "is_unique",
    "sat_calls",
    "runtime_ms",
    "matches_hidden_solution",
)


def _discover_all_puzzles(puzzles_dir: Path = PUZZLES_DIR) -> list[tuple[str, Path]]:
    items: list[tuple[str, Path]] = []
    for sub in ("3x3", "4x4", "5x5"):
        for p in sorted((puzzles_dir / sub).glob("*.json")):
            items.append(("standard", p))
    for p in sorted((puzzles_dir / "extensions").glob("*.json")):
        items.append(("extension", p))
    for p in sorted((puzzles_dir / "edge_cases").glob("*.json")):
        items.append(("edge_case", p))
    return items


def generate_uniqueness_report(
    out_csv: Path = DEFAULT_OUTPUT_CSV,
    puzzles_dir: Path = PUZZLES_DIR,
) -> list[dict[str, Any]]:
    """Verify uniqueness across all puzzles and write `out_csv`."""
    sel = make_encoder("direct")
    assert sel.encoder is not None
    solver = make_solver()

    rows: list[dict[str, Any]] = []
    for group, path in _discover_all_puzzles(puzzles_dir):
        puzzle = load_puzzle_definition(path)
        engine = GameEngine()
        engine.load_puzzle(path)
        clues = engine.get_all_clues_for_uniqueness()

        t0 = time.perf_counter()
        res = check_uniqueness(clues, puzzle.grid_size, sel.encoder, solver)
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        sat_calls = 1 if res.solution_count_status == "UNSAT" else 2
        if res.is_unique and res.first_model is not None:
            hidden_status = {ch.cell_id: ch.hidden_status for ch in puzzle.characters}
            matches = str(dict(res.first_model) == hidden_status).lower()
        else:
            matches = "NA"

        rows.append(
            {
                "puzzle_id": puzzle.puzzle_id,
                "group": group,
                "grid_size": puzzle.grid_size,
                "encoding": sel.effective_encoding,
                "status": res.solution_count_status,
                "is_unique": str(res.is_unique).lower(),
                "sat_calls": sat_calls,
                "runtime_ms": elapsed_ms,
                "matches_hidden_solution": matches,
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export puzzle uniqueness report CSV.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_CSV)
    args = parser.parse_args(argv)
    rows = generate_uniqueness_report(out_csv=args.out)
    print(f"Uniqueness report written ({len(rows)} puzzles) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
