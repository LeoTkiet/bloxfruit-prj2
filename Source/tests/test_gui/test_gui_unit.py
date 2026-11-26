"""Isolated PyQt6 GUI unit tests using MockGameEngine & MockGuiLogicAgent."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from core.contracts.models import HintResult, Status, UniquenessResult
from gui.main_window import MainWindow
from tests.test_gui.mock_engine import MockGameEngine, MockGuiLogicAgent


def _create_window(qtbot) -> tuple[MainWindow, MockGameEngine, MockGuiLogicAgent]:
    engine = MockGameEngine()
    agent = MockGuiLogicAgent()
    win = MainWindow(engine=engine, agent=agent, puzzles_dir=None)
    qtbot.addWidget(win)
    win.show()
    return win, engine, agent


def test_initial_render_and_no_hidden_leakage(qtbot) -> None:
    win, _, _ = _create_window(qtbot)

    assert win.board_widget.grid_size == 3
    # Revealed card A1 displays status and clue
    a1 = win.board_widget.get_card("A1")
    assert a1.is_revealed is True
    assert a1.status == Status.INNOCENT
    assert "Exactly 2 Criminals in {B1, C2}." in a1.clue_label.text()

    # Face-down card B1 MUST NOT reveal hidden status or hidden clue
    b1 = win.board_widget.get_card("B1")
    assert b1.is_revealed is False
    assert b1.status == Status.UNKNOWN
    assert "C1 is Innocent" not in b1.clue_label.text()
    assert "CRIMINAL" not in b1.status_badge.text()
    assert "Face-down" in b1.clue_label.text()


def test_click_revealed_card_highlights_clue_region(qtbot) -> None:
    win, engine, _ = _create_window(qtbot)

    a1 = win.board_widget.get_card("A1")
    qtbot.mouseClick(a1, Qt.MouseButton.LeftButton)

    assert engine.highlight_calls == ["A1"]
    assert win.board_widget.highlighted_cells == frozenset({"B1", "C2"})
    assert win.board_widget.get_card("B1").is_region_highlighted is True
    assert win.board_widget.get_card("C2").is_region_highlighted is True
    assert win.board_widget.get_card("A2").is_region_highlighted is False

    # Clicking A1 again toggles highlight off
    qtbot.mouseClick(a1, Qt.MouseButton.LeftButton)
    assert win.board_widget.highlighted_cells == frozenset()


def test_manual_verdict_distinguishes_all_verdict_codes(qtbot) -> None:
    win, _, _ = _create_window(qtbot)

    # 1. NOT_PROVABLE on C1 -> rejected, card remains face-down
    c1 = win.board_widget.get_card("C1")
    qtbot.mouseClick(c1, Qt.MouseButton.LeftButton)
    assert win.btn_mark_criminal.isEnabled()
    qtbot.mouseClick(win.btn_mark_criminal, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "NOT_PROVABLE"
    assert "NOT PROVABLE" in win.feedback_banner.text()
    assert c1.is_revealed is False

    # 2. CONTRADICTED on B1 as INNOCENT -> rejected distinctly, card remains face-down
    b1 = win.board_widget.get_card("B1")
    qtbot.mouseClick(b1, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(win.btn_mark_innocent, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "CONTRADICTED"
    assert "CONTRADICTED" in win.feedback_banner.text()
    assert b1.is_revealed is False

    # 3. INCONSISTENT on A2 as CRIMINAL -> warns inconsistent, card stays face-down
    a2 = win.board_widget.get_card("A2")
    qtbot.mouseClick(a2, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(win.btn_mark_criminal, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "INCONSISTENT"
    assert a2.is_revealed is False

    # 4. ACCEPTED on B1 as CRIMINAL -> flips card and reveals its clue
    qtbot.mouseClick(b1, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(win.btn_mark_criminal, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "ACCEPTED"
    assert b1.is_revealed is True
    assert b1.status == Status.CRIMINAL
    assert "C1 is Innocent." in b1.clue_label.text()
    assert win.trace_panel.step_count == 4


def test_hint_highlights_target_and_relevant_clues(qtbot) -> None:
    win, _, agent = _create_window(qtbot)

    qtbot.mouseClick(win.btn_hint, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "HINT"
    assert win.board_widget.get_card("B1").is_hint_target is True
    assert win.board_widget.get_card("A1").is_hint_clue_source is True
    assert win.board_widget.selected_cell == "B1"

    # Ambiguous hint
    agent.hint_to_return = HintResult(
        cell=None,
        forced_status=Status.UNKNOWN,
        relevant_clue_ids=("clue_C3",),
        message="No forced character (AMBIGUOUS).",
    )
    qtbot.mouseClick(win.btn_hint, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "AMBIGUOUS"
    assert win.board_widget.get_card("C3").is_hint_clue_source is True

    # Inconsistent hint
    agent.hint_to_return = HintResult(
        cell=None,
        forced_status=Status.UNKNOWN,
        message="KB is UNSAT.",
        is_inconsistent=True,
    )
    qtbot.mouseClick(win.btn_hint, Qt.MouseButton.LeftButton)
    assert win.feedback_banner.property("feedbackKind") == "INCONSISTENT"


def test_restart_resets_board_trace_and_agent_cache(qtbot) -> None:
    win, engine, agent = _create_window(qtbot)
    initial_clears = agent.clear_cache_calls
    initial_resets = agent.reset_stats_calls

    win.submit_verdict("B1", Status.CRIMINAL)
    assert win.board_widget.get_card("B1").is_revealed is True
    assert win.trace_panel.step_count == 1

    qtbot.mouseClick(win.btn_restart, Qt.MouseButton.LeftButton)
    assert engine.restart_calls == 1
    assert agent.clear_cache_calls == initial_clears + 1
    assert agent.reset_stats_calls == initial_resets + 1
    assert win.board_widget.get_card("B1").is_revealed is False
    assert win.trace_panel.step_count == 0


def test_auto_solve_solved_ambiguous_and_inconsistent(qtbot) -> None:
    win, _, agent = _create_window(qtbot)
    fast_idx = win.speed_combo.findData(0)
    win.speed_combo.setCurrentIndex(fast_idx)

    # 1. SOLVED
    agent.auto_solve_mode = "SOLVED"
    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "SOLVED"
    assert win.trace_panel.step_count == 7
    assert win.trace_panel.tile_progress.value_lbl.text() == "9 / 9"

    # 2. AMBIGUOUS
    win.restart_puzzle()
    agent.auto_solve_mode = "AMBIGUOUS"
    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "AMBIGUOUS"

    # 3. INCONSISTENT
    win.restart_puzzle()
    agent.auto_solve_mode = "INCONSISTENT"
    qtbot.mouseClick(win.btn_auto_solve, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._worker is None, timeout=5000)
    assert win.feedback_banner.property("feedbackKind") == "INCONSISTENT"


def test_uniqueness_check_updates_badge(qtbot) -> None:
    win, _, agent = _create_window(qtbot)

    agent.uniqueness_to_return = UniquenessResult(
        is_unique=True, solution_count_status="UNIQUE"
    )
    qtbot.mouseClick(win.btn_uniqueness, Qt.MouseButton.LeftButton)
    assert "UNIQUE" in win.trace_panel.uniqueness_badge.text()

    agent.uniqueness_to_return = UniquenessResult(
        is_unique=False, solution_count_status="MULTIPLE"
    )
    qtbot.mouseClick(win.btn_uniqueness, Qt.MouseButton.LeftButton)
    assert "MULTIPLE" in win.trace_panel.uniqueness_badge.text()

    agent.uniqueness_to_return = UniquenessResult(
        is_unique=False, solution_count_status="UNSAT"
    )
    qtbot.mouseClick(win.btn_uniqueness, Qt.MouseButton.LeftButton)
    assert "UNSAT" in win.trace_panel.uniqueness_badge.text()
