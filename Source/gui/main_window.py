"""Main application window for Griductive Solver — Warm Classic Detective Board (TV5).

Interacts strictly through `IGameEngine` and `ILogicAgent` contracts via
Dependency Injection — never accesses hidden puzzle data directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.contracts.interfaces import IGameEngine, ILogicAgent
from core.contracts.models import (
    CellID,
    DeductionStep,
    HintResult,
    PublicState,
    Status,
    VerdictCode,
)
from gui.board_widget import BoardWidget
from gui.theme import APP_STYLESHEET, PALETTE, build_banner_stylesheet
from gui.trace_panel import TracePanel
from gui.worker import AutoSolveWorker


SPEED_PRESETS: tuple[tuple[str, int], ...] = (
    ("Normal (450 ms)", 450),
    ("Slow (900 ms)", 900),
    ("Instant (0 ms)", 0),
)


def discover_puzzle_files(puzzles_dir: Optional[Path]) -> list[Path]:
    """Return sorted JSON puzzle paths under `puzzles_dir`."""
    if puzzles_dir is None or not puzzles_dir.exists():
        return []
    return sorted(puzzles_dir.rglob("*.json"))


class MainWindow(QMainWindow):
    """Primary desktop GUI for playing and auto-solving Griductive puzzles."""

    def __init__(
        self,
        engine: IGameEngine,
        agent: ILogicAgent,
        *,
        puzzles_dir: Optional[Path] = None,
        initial_puzzle: Optional[Path] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._engine: IGameEngine = engine
        self._agent: ILogicAgent = agent
        self._puzzles_dir: Optional[Path] = puzzles_dir
        self._current_state: Optional[PublicState] = None
        self._current_puzzle_path: Optional[Path] = None
        self._worker: Optional[AutoSolveWorker] = None
        self._puzzle_catalog: list[Path] = discover_puzzle_files(puzzles_dir)

        self.setWindowTitle("Griductive Solver — Case Investigation Board")
        self.resize(1300, 810)
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_ui()
        self._setup_shortcuts()

        target = initial_puzzle or (
            self._puzzle_catalog[0] if self._puzzle_catalog else None
        )
        if target is not None:
            self.load_puzzle_file(target)
        else:
            try:
                state = self._engine.get_public_state()
                self._apply_fresh_puzzle_state(state)
            except RuntimeError:
                self._set_feedback(
                    "INFO",
                    "Open a case file via 'Load' or choose a puzzle from the case selector.",
                )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        # 1. Espresso Walnut Top Masthead Bar
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        app_title = QLabel("GRIDUCTIVE")
        app_title.setStyleSheet(
            f"font-family: Georgia, 'Times New Roman', serif; font-size: 17px; "
            f"font-weight: 700; letter-spacing: 1.4px; color: {PALETTE['cream_ink']};"
        )
        self.puzzle_subtitle = QLabel("No case file loaded")
        self.puzzle_subtitle.setStyleSheet(
            f"font-size: 11px; color: {PALETTE['cream_sub']};"
        )
        title_box.addWidget(app_title)
        title_box.addWidget(self.puzzle_subtitle)
        top_layout.addLayout(title_box)

        top_layout.addSpacing(8)

        # Quick puzzle selector (explicit size policy prevents overlap)
        self.puzzle_combo = QComboBox()
        self.puzzle_combo.setMinimumWidth(210)
        self.puzzle_combo.setMaximumWidth(280)
        self.puzzle_combo.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.puzzle_combo.setToolTip("Quick-select a case file from Source/puzzles/")
        self._populate_puzzle_combo()
        self.puzzle_combo.currentIndexChanged.connect(self._on_combo_puzzle_selected)
        top_layout.addWidget(self.puzzle_combo)

        top_layout.addStretch(1)

        # 4 Mandatory Buttons: Load, Restart, Hint, Auto Solve + Uniqueness
        self.btn_load = QPushButton("Load")
        self.btn_load.setMinimumWidth(68)
        self.btn_load.setToolTip("Load a puzzle JSON file from disk")
        self.btn_load.clicked.connect(self._on_load_clicked)
        top_layout.addWidget(self.btn_load)

        self.btn_restart = QPushButton("Restart")
        self.btn_restart.setMinimumWidth(76)
        self.btn_restart.setToolTip("Reset current case back to step 0 (R)")
        self.btn_restart.clicked.connect(self.restart_puzzle)
        top_layout.addWidget(self.btn_restart)

        self.btn_hint = QPushButton("Hint")
        self.btn_hint.setObjectName("HintBtn")
        self.btn_hint.setMinimumWidth(68)
        self.btn_hint.setToolTip("Ask Logic Agent for a provable next move (H)")
        self.btn_hint.clicked.connect(self.request_hint)
        top_layout.addWidget(self.btn_hint)

        self.speed_combo = QComboBox()
        self.speed_combo.setMinimumWidth(135)
        self.speed_combo.setToolTip("Auto Solve playback speed")
        for label, ms in SPEED_PRESETS:
            self.speed_combo.addItem(label, ms)
        top_layout.addWidget(self.speed_combo)

        self.btn_auto_solve = QPushButton("Auto Solve")
        self.btn_auto_solve.setObjectName("PrimaryBtn")
        self.btn_auto_solve.setMinimumWidth(102)
        self.btn_auto_solve.setToolTip("Run the no-guess Deductive Logic Agent")
        self.btn_auto_solve.clicked.connect(self.start_auto_solve)
        top_layout.addWidget(self.btn_auto_solve)

        self.btn_uniqueness = QPushButton("Uniqueness")
        self.btn_uniqueness.setMinimumWidth(96)
        self.btn_uniqueness.setToolTip(
            "Verify whether the complete clue set admits a unique solution"
        )
        self.btn_uniqueness.clicked.connect(self.run_uniqueness_check)
        top_layout.addWidget(self.btn_uniqueness)

        root.addWidget(top_bar)

        # 2. Case Feedback Banner
        self.feedback_banner = QLabel("")
        self.feedback_banner.setObjectName("FeedbackBanner")
        self.feedback_banner.setWordWrap(True)
        self._set_feedback("INFO", "Ready.")
        root.addWidget(self.feedback_banner)

        # 3. Main Split Workspace (Left: Cork Board + Verdict Bar | Right: Case Ledger)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        board_container = QFrame()
        board_container.setObjectName("BoardContainer")
        board_box = QVBoxLayout(board_container)
        board_box.setContentsMargins(6, 6, 6, 6)
        self.board_widget = BoardWidget(board_container)
        self.board_widget.cell_clicked.connect(self._on_cell_clicked)
        board_box.addWidget(self.board_widget)
        left_layout.addWidget(board_container, stretch=1)

        # Manual Verdict Action Bar (generous padding & widths so labels never clip)
        action_bar = QFrame()
        action_bar.setObjectName("ActionBar")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 9, 14, 9)
        action_layout.setSpacing(10)

        self.selection_label = QLabel(
            "Click a sealed dossier to judge, or an open card to trace clues."
        )
        self.selection_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {PALETTE['ink_secondary']}; "
            f"background: transparent;"
        )
        action_layout.addWidget(self.selection_label, stretch=1)

        self.btn_mark_criminal = QPushButton("Mark CRIMINAL (C)")
        self.btn_mark_criminal.setObjectName("CriminalBtn")
        self.btn_mark_criminal.setMinimumWidth(164)
        self.btn_mark_criminal.setEnabled(False)
        self.btn_mark_criminal.clicked.connect(
            lambda: self.submit_selected_verdict(Status.CRIMINAL)
        )
        action_layout.addWidget(self.btn_mark_criminal)

        self.btn_mark_innocent = QPushButton("Mark INNOCENT (I)")
        self.btn_mark_innocent.setObjectName("InnocentBtn")
        self.btn_mark_innocent.setMinimumWidth(164)
        self.btn_mark_innocent.setEnabled(False)
        self.btn_mark_innocent.clicked.connect(
            lambda: self.submit_selected_verdict(Status.INNOCENT)
        )
        action_layout.addWidget(self.btn_mark_innocent)

        self.btn_clear_hl = QPushButton("Clear")
        self.btn_clear_hl.setMinimumWidth(72)
        self.btn_clear_hl.setToolTip("Clear selection and clue traces (Esc)")
        self.btn_clear_hl.clicked.connect(self._on_clear_highlights)
        action_layout.addWidget(self.btn_clear_hl)

        left_layout.addWidget(action_bar)

        self.trace_panel = TracePanel()

        splitter.addWidget(left_pane)
        splitter.addWidget(self.trace_panel)
        splitter.setStretchFactor(0, 64)
        splitter.setStretchFactor(1, 36)
        splitter.setSizes([810, 460])

        root.addWidget(splitter, stretch=1)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("C"), self, activated=self._shortcut_criminal)
        QShortcut(QKeySequence("I"), self, activated=self._shortcut_innocent)
        QShortcut(QKeySequence("H"), self, activated=self._shortcut_hint)
        QShortcut(QKeySequence("R"), self, activated=self._shortcut_restart)
        QShortcut(QKeySequence("Escape"), self, activated=self._on_clear_highlights)

    def _shortcut_criminal(self) -> None:
        if self.btn_mark_criminal.isEnabled():
            self.submit_selected_verdict(Status.CRIMINAL)

    def _shortcut_innocent(self) -> None:
        if self.btn_mark_innocent.isEnabled():
            self.submit_selected_verdict(Status.INNOCENT)

    def _shortcut_hint(self) -> None:
        if self.btn_hint.isEnabled():
            self.request_hint()

    def _shortcut_restart(self) -> None:
        if self.btn_restart.isEnabled():
            self.restart_puzzle()

    def _populate_puzzle_combo(self) -> None:
        self.puzzle_combo.blockSignals(True)
        self.puzzle_combo.clear()
        if not self._puzzle_catalog:
            self.puzzle_combo.addItem("(No preset cases)", None)
        else:
            for p in self._puzzle_catalog:
                if self._puzzles_dir is not None:
                    try:
                        label = str(p.relative_to(self._puzzles_dir)).replace("\\", "/")
                    except ValueError:
                        label = p.name
                else:
                    label = p.name
                self.puzzle_combo.addItem(label, str(p))
        self.puzzle_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reset_agent_cache_and_stats(self) -> None:
        """Follow TV4's convention: clear KB cache and SAT counters on Load/Restart."""
        clear_fn = getattr(self._agent, "clear_cache", None)
        if callable(clear_fn):
            clear_fn()
        reset_fn = getattr(self._agent, "reset_stats", None)
        if callable(reset_fn):
            reset_fn()

    def _set_feedback(self, kind: str, message: str) -> None:
        self.feedback_banner.setText(message)
        self.feedback_banner.setProperty("feedbackKind", kind)
        self.feedback_banner.setStyleSheet(build_banner_stylesheet(kind))

    def _set_controls_busy(self, busy: bool) -> None:
        self.puzzle_combo.setEnabled(not busy)
        self.btn_load.setEnabled(not busy)
        self.btn_restart.setEnabled(not busy and self._current_state is not None)
        self.btn_hint.setEnabled(not busy and self._current_state is not None)
        self.btn_uniqueness.setEnabled(not busy and self._current_state is not None)
        self.speed_combo.setEnabled(not busy)

        if busy:
            self.btn_auto_solve.setText("Finish Fast")
            self.btn_auto_solve.setObjectName("DangerBtn")
            self.btn_mark_criminal.setEnabled(False)
            self.btn_mark_innocent.setEnabled(False)
        else:
            self.btn_auto_solve.setText("Auto Solve")
            self.btn_auto_solve.setObjectName("PrimaryBtn")
            self._update_verdict_buttons()
        self.btn_auto_solve.style().unpolish(self.btn_auto_solve)
        self.btn_auto_solve.style().polish(self.btn_auto_solve)

    def _update_verdict_buttons(self) -> None:
        sel = self.board_widget.selected_cell
        has_valid_selection = (
            self._current_state is not None
            and not self._current_state.is_solved
            and sel is not None
            and not self._current_state.get_character(sel).is_revealed
            and self._worker is None
        )
        self.btn_mark_criminal.setEnabled(has_valid_selection)
        self.btn_mark_innocent.setEnabled(has_valid_selection)

        if has_valid_selection and sel is not None and self._current_state is not None:
            ch = self._current_state.get_character(sel)
            self.selection_label.setText(
                f"Selected Dossier: {ch.cell_id} — {ch.name} ({ch.profession})"
            )
        elif self._current_state is not None and self._current_state.is_solved:
            self.selection_label.setText(
                "Case Closed — click any revealed dossier to inspect its clue links."
            )
        else:
            self.selection_label.setText(
                "Click a sealed dossier to judge, or an open card to trace clues."
            )

    def _update_puzzle_subtitle(self, state: PublicState) -> None:
        self.puzzle_subtitle.setText(
            f"Case: {state.puzzle_name}  •  {state.grid_size}×{state.grid_size} Grid  •  "
            f"{len(state.revealed_cells)}/{len(state.characters)} Open"
        )

    def _apply_fresh_puzzle_state(self, state: PublicState) -> None:
        self._current_state = state
        self._reset_agent_cache_and_stats()
        self.board_widget.clear_highlights()
        self.board_widget.render_state(state)
        self.trace_panel.reset(state)
        self._update_puzzle_subtitle(state)
        self._set_controls_busy(False)
        self._set_feedback(
            "INFO",
            f"Case opened: '{state.puzzle_name}' ({state.grid_size}×{state.grid_size}). "
            f"No-Guess Rule enforced — only logically entailed verdicts are accepted.",
        )

    # ------------------------------------------------------------------
    # Actions: Load, Restart, Card Click, Submit Verdict, Hint, Auto Solve
    # ------------------------------------------------------------------

    def _on_combo_puzzle_selected(self, index: int) -> None:
        path_str = self.puzzle_combo.itemData(index)
        if not path_str:
            return
        self.load_puzzle_file(Path(path_str))

    def _on_load_clicked(self) -> None:
        start_dir = str(self._puzzles_dir) if self._puzzles_dir else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Griductive Case File (JSON)",
            start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        self.load_puzzle_file(Path(file_path))

    def load_puzzle_file(self, path: Path) -> bool:
        """Load a puzzle JSON file through `IGameEngine.load_puzzle`."""
        if self._worker is not None:
            return False
        try:
            state = self._engine.load_puzzle(path)
        except Exception as exc:
            self._set_feedback("CONTRADICTED", f"Failed to load case file: {exc}")
            return False

        self._current_puzzle_path = path
        resolved_str = str(path)
        for idx in range(self.puzzle_combo.count()):
            if self.puzzle_combo.itemData(idx) == resolved_str:
                self.puzzle_combo.blockSignals(True)
                self.puzzle_combo.setCurrentIndex(idx)
                self.puzzle_combo.blockSignals(False)
                break

        self._apply_fresh_puzzle_state(state)
        return True

    def restart_puzzle(self) -> None:
        """Reset the currently loaded puzzle via `IGameEngine.restart`."""
        if self._worker is not None or self._current_state is None:
            return
        try:
            state = self._engine.restart()
        except Exception as exc:
            self._set_feedback("CONTRADICTED", f"Restart failed: {exc}")
            return
        self._apply_fresh_puzzle_state(state)
        self._set_feedback(
            "INFO",
            f"Case '{state.puzzle_name}' reset back to initial clues (step 0).",
        )

    def _on_cell_clicked(self, cell_id: CellID) -> None:
        if self._current_state is None or self._worker is not None:
            return

        char_info = self._current_state.get_character(cell_id)
        if char_info.is_revealed:
            if self.board_widget.active_clue_source == cell_id:
                self.board_widget.set_clue_highlight(None, ())
                self._set_feedback("INFO", f"Cleared clue trace for {cell_id}.")
            else:
                highlighted = self._engine.get_highlighted_cells(cell_id)
                self.board_widget.set_clue_highlight(cell_id, highlighted)
                targets_str = ", ".join(highlighted) if highlighted else "none"
                self._set_feedback(
                    "INFO",
                    f"Tracing clue on {cell_id} ({char_info.name}) -> "
                    f"referenced cells: [{targets_str}].",
                )
        else:
            if self.board_widget.selected_cell == cell_id:
                self.board_widget.set_selected_cell(None)
            else:
                self.board_widget.set_selected_cell(cell_id)
            self._update_verdict_buttons()

    def _on_clear_highlights(self) -> None:
        if self._worker is not None:
            return
        self.board_widget.clear_highlights()
        self._update_verdict_buttons()

    def submit_selected_verdict(self, status: Status) -> None:
        """Submit manual CRIMINAL / INNOCENT verdict for the selected cell."""
        if self._current_state is None or self._worker is not None:
            return
        cell_id = self.board_widget.selected_cell
        if cell_id is None:
            return
        self.submit_verdict(cell_id, status)

    def submit_verdict(self, cell_id: CellID, status: Status) -> None:
        """Submit a verdict through `IGameEngine.submit_verdict` and handle all VerdictCodes."""
        if self._current_state is None or self._worker is not None:
            return

        active_clues_before = tuple(c.clue_id for c in self._current_state.revealed_clues)
        try:
            response = self._engine.submit_verdict(cell_id, status)
        except Exception as exc:
            self._set_feedback("CONTRADICTED", f"Verdict error: {exc}")
            return

        self._current_state = response.public_state
        self.board_widget.render_state(self._current_state)
        self._update_puzzle_subtitle(self._current_state)
        self.trace_panel.update_progress(self._current_state)
        self.trace_panel.record_manual_verdict(response, active_clues_before)

        if response.code == VerdictCode.ACCEPTED:
            self.board_widget.clear_highlights()
            if self._current_state.is_solved:
                self._set_feedback(
                    "SOLVED",
                    f"CASE SOLVED — {response.message} All {len(self._current_state.characters)} "
                    f"dossiers proved strictly by logic.",
                )
            else:
                self._set_feedback("ACCEPTED", f"ACCEPTED — {response.message}")
        elif response.code == VerdictCode.NOT_PROVABLE:
            self._set_feedback(
                "NOT_PROVABLE",
                f"NOT PROVABLE (No Guessing Allowed) — {response.message} "
                f"Dossier {cell_id} remains sealed.",
            )
        elif response.code == VerdictCode.CONTRADICTED:
            self._set_feedback(
                "CONTRADICTED",
                f"CONTRADICTED — {response.message} Dossier {cell_id} remains sealed.",
            )
        elif response.code == VerdictCode.INCONSISTENT:
            self._set_feedback(
                "INCONSISTENT",
                f"INCONSISTENT KB — {response.message}",
            )

        self._update_verdict_buttons()

    def request_hint(self) -> Optional[HintResult]:
        """Request a purely public-knowledge hint via `ILogicAgent.get_hint`."""
        if self._current_state is None or self._worker is not None:
            return None
        if self._current_state.is_solved:
            self._set_feedback("SOLVED", "Case is already solved — no hint needed.")
            return None

        try:
            hint = self._agent.get_hint(self._current_state)
        except Exception as exc:
            self._set_feedback("CONTRADICTED", f"Hint failed: {exc}")
            return None

        clue_id_to_owner = {
            c.clue_id: c.owner for c in self._current_state.revealed_clues
        }
        relevant_owners = [
            clue_id_to_owner[cid]
            for cid in hint.relevant_clue_ids
            if cid in clue_id_to_owner
        ]

        if hint.is_inconsistent:
            self.board_widget.clear_highlights()
            self._set_feedback(
                "INCONSISTENT",
                f"INCONSISTENT KB — {hint.message or 'Public clues are mutually contradictory.'}",
            )
        elif hint.cell is not None:
            self.board_widget.set_hint_highlight(hint.cell, relevant_owners)
            self._update_verdict_buttons()
            clues_note = (
                f" Supporting clues: {', '.join(relevant_owners)}."
                if relevant_owners
                else ""
            )
            msg = hint.message or (
                f"{hint.cell} is logically forced to be {hint.forced_status.value}."
            )
            prefix = "" if msg.upper().startswith("HINT") else "HINT — "
            self._set_feedback("HINT", f"{prefix}{msg}{clues_note}")
        else:
            self.board_widget.set_hint_highlight(None, relevant_owners)
            self._update_verdict_buttons()
            msg = hint.message or (
                "No dossier is currently logically forced (AMBIGUOUS). "
                "No guessing allowed."
            )
            self._set_feedback("AMBIGUOUS", f"AMBIGUOUS — {msg}")

        return hint

    def start_auto_solve(self) -> None:
        """Start background Auto Solve (or skip animation delay if already running)."""
        if self._worker is not None:
            self._worker.skip_remaining_delays()
            return
        if self._current_state is None:
            return
        if self._current_state.is_solved:
            self._set_feedback("SOLVED", "Case is already solved.")
            return

        delay_ms = int(self.speed_combo.currentData() or 0)
        self.board_widget.clear_highlights()
        self._worker = AutoSolveWorker(
            self._agent,
            self._engine,
            delay_ms=delay_ms,
            parent=self,
        )
        self._worker.step_produced.connect(self._on_auto_step)
        self._worker.finished_solve.connect(self._on_auto_finished)
        self._worker.failed.connect(self._on_auto_failed)
        self._set_controls_busy(True)
        self._set_feedback(
            "INFO",
            "Auto Solve running — Deductive Logic Agent evaluating entailments...",
        )
        self._worker.start()

    def _release_worker(self) -> None:
        """Wait briefly for the worker thread to finish exiting before clearing reference."""
        worker = self._worker
        if worker is not None:
            if worker.isRunning():
                worker.wait(500)
            worker.deleteLater()
        self._worker = None

    def _on_auto_step(self, step: DeductionStep, snapshot: PublicState) -> None:
        self._current_state = snapshot
        self.board_widget.render_state(snapshot)
        self._update_puzzle_subtitle(snapshot)
        if step.cell is not None and step.verdict_code == VerdictCode.ACCEPTED:
            self.board_widget.set_clue_highlight(step.cell, ())
            ch = snapshot.get_character(step.cell)
            self._set_feedback(
                "ACCEPTED",
                f"Step #{step.step_number} — Proved {step.cell} ({ch.name}) is "
                f"{step.verdict.value} ({len(step.active_clue_ids)} active clues).",
            )
        self.trace_panel.update_progress(snapshot)
        self.trace_panel.append_step(step)

    def _on_auto_finished(
        self,
        steps: list[DeductionStep],
        final_state: PublicState,
    ) -> None:
        self._release_worker()
        self._current_state = final_state
        self.board_widget.clear_highlights()
        self.board_widget.render_state(final_state)
        self._update_puzzle_subtitle(final_state)
        self.trace_panel.update_progress(final_state)
        self._set_controls_busy(False)

        if final_state.is_solved:
            self._set_feedback(
                "SOLVED",
                f"CASE SOLVED — Auto Solve proved all dossiers in {len(steps)} "
                f"logical step(s) with zero guessing.",
            )
            return

        last_code = steps[-1].verdict_code if steps else VerdictCode.NOT_PROVABLE
        if last_code in (VerdictCode.INCONSISTENT, VerdictCode.CONTRADICTED):
            self._set_feedback(
                "INCONSISTENT",
                "AUTO SOLVE STOPPED — INCONSISTENT knowledge base detected (UNSAT).",
            )
        else:
            remaining = ", ".join(final_state.unsolved_cells)
            self._set_feedback(
                "AMBIGUOUS",
                f"AUTO SOLVE STOPPED — AMBIGUOUS state reached (no forced move; "
                f"refused to guess). Remaining sealed: [{remaining}].",
            )

    def _on_auto_failed(self, error_msg: str) -> None:
        self._release_worker()
        self._set_controls_busy(False)
        self._set_feedback("CONTRADICTED", f"Auto Solve error: {error_msg}")

    def run_uniqueness_check(self) -> None:
        """Verify puzzle solution uniqueness on the complete clue set."""
        if self._current_state is None or self._worker is not None:
            return
        try:
            all_clues = self._engine.get_all_clues_for_uniqueness()
            result = self._agent.check_uniqueness(
                all_clues,
                self._current_state.grid_size,
            )
        except Exception as exc:
            self._set_feedback("CONTRADICTED", f"Uniqueness check failed: {exc}")
            return

        self.trace_panel.set_uniqueness_result(result)
        if result.is_unique and result.solution_count_status == "UNIQUE":
            self._set_feedback(
                "ACCEPTED",
                "UNIQUENESS VERIFIED — Complete clue set admits exactly ONE valid assignment.",
            )
        elif result.solution_count_status == "UNSAT":
            self._set_feedback(
                "INCONSISTENT",
                "UNIQUENESS FAILED — Complete clue set is UNSAT (no valid assignment).",
            )
        else:
            self._set_feedback(
                "AMBIGUOUS",
                "UNIQUENESS WARNING — Multiple valid assignments exist (ambiguous case).",
            )

    def closeEvent(self, event) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.skip_remaining_delays()
            self._worker.requestInterruption()
            self._worker.wait(3000)
        super().closeEvent(event)
