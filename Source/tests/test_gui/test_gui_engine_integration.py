"""Milestone 2 Integration Tests: Real TV1 GameEngine + TV5 MainWindow on real JSON puzzles."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt

from core.contracts.models import Status
from engine.game_engine import GameEngine
from gui.main_window import MainWindow
from tests.test_engine.mock_agent import ExactTestOracleAgent

PUZZLES_DIR = Path(__file__).resolve().parent.parent.parent / "puzzles"


def _make_integrated_window(qtbot, rel_puzzle: str) -> MainWindow:
    agent = ExactTestOracleAgent()
    engine = GameEngine(logic_agent=agent)
    win = MainWindow(
        engine=engine,
        agent=agent,
        puzzles_dir=PUZZLES_DIR,
        initial_puzzle=PUZZLES_DIR / rel_puzzle,
    )
    qtbot.addWidget(win)
    win.show()
    # Set speed to Fast (0 ms)
    fast_idx = win.speed_combo.findData(0)
    win.speed_combo.setCurrentIndex(fast_idx)
    return win


def test_real_3x3_load_highlight_hint_manual_and_autosolve(qtbot) -> None:
    win = _make_integrated_window(qtbot, "3x3/3x3_01_precinct_basics.json")

    assert win.board_widget.grid_size == 3
    assert win.board_widget.get_card("A1").is_revealed is True
    assert win.board_widget.get_card("B1").is_revealed is False

    # Highlight clue on A1 ("Exactly 2 Criminals in {B1, C2}.")
    qtbot.mouseClick(win.board_widget.get_card("A1"), Qt.MouseButton.LeftButton)
    assert win.board_widget.highlighted_cells == frozenset({"B1", "C2"})

    # Reject wrong guess on B1 (INNOCENT is contradicted because B1 must be CRIMINAL)
    win.submit_verdict("B1", Status.INNOCENT)
    assert win.feedback_banner.property("feedbackKind") == "CONTRADICTED"
    assert win.board_widget.get_card("B1").is_revealed is False

    # Hint should point to a forced character
    hint = win.request_hint()
    assert hint is not None and hint.cell is not None

    # Auto Solve completes entire 3x3 puzzle step-by-step without guessing
    revealed_counts: list[int] = []
    orig_on_step = win._on_auto_step

    def _spy_on_step(step, snapshot):
        revealed_counts.append(len(snapshot.revealed_cells))
        orig_on_step(step, snapshot)

    win._on_auto_step = _spy_on_step  # type: ignore[method-assign]
    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "SOLVED"
    assert win.trace_panel.tile_progress.value_lbl.text() == "9 / 9"
    # Verify progressive intermediate board states (strictly increasing, not jumping to 9 immediately)
    assert revealed_counts == [3, 4, 5, 6, 7, 8, 9]

    # Restart restores step 0
    win.restart_puzzle()
    assert win.trace_panel.tile_progress.value_lbl.text() == "2 / 9"


def test_real_4x4_and_5x5_board_scaling(qtbot) -> None:
    win = _make_integrated_window(qtbot, "4x4/4x4_01_city_grid.json")
    assert win.board_widget.grid_size == 4
    assert win.board_widget.get_card("D4").cell_id == "D4"

    ok = win.load_puzzle_file(PUZZLES_DIR / "5x5/5x5_01_grand_precinct.json")
    assert ok is True
    assert win.board_widget.grid_size == 5
    assert win.board_widget.get_card("E5").cell_id == "E5"


def test_real_edge_case_ambiguous_stops_without_guessing(qtbot) -> None:
    win = _make_integrated_window(qtbot, "edge_cases/edge_3x3_01_ambiguous.json")

    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "AMBIGUOUS"


def test_real_edge_case_inconsistent_detected_cleanly(qtbot) -> None:
    win = _make_integrated_window(qtbot, "edge_cases/edge_3x3_02_inconsistent.json")

    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "INCONSISTENT"
