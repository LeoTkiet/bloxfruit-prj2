"""Archival Case Ledger: Deduction Trace and Live Telemetry panel (TV5).

Replaces generic boxed KPI tiles with a unified ruled archival ledger strip
(clean typographic hierarchy with vertical sepia hairlines), paired with a
deduction log table and a typewriter-styled Step Inspector.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.contracts.models import (
    DeductionStep,
    PublicState,
    Status,
    UniquenessResult,
    VerdictCode,
    VerdictResponse,
)
from gui.clue_formatter import format_clue
from gui.theme import PALETTE


class _LedgerStat(QWidget):
    """Single ruled stat column inside the archival telemetry strip."""

    def __init__(self, label: str, initial: str = "—", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(1)

        self.title_lbl = QLabel(label)
        self.title_lbl.setStyleSheet(
            f"color: {PALETTE['ink_muted']}; font-size: 9px; font-weight: 700; "
            f"letter-spacing: 0.5px; background: transparent;"
        )
        self.value_lbl = QLabel(initial)
        self.value_lbl.setStyleSheet(
            f"color: {PALETTE['ink_primary']}; font-size: 13px; font-weight: 800; "
            f"font-family: Consolas, monospace; background: transparent;"
        )
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)

    def set_value(self, value: str) -> None:
        self.value_lbl.setText(value)


def _v_divider() -> QFrame:
    line = QFrame()
    line.setFixedWidth(1)
    line.setStyleSheet(f"background-color: {PALETTE['sepia_border']}; border: none;")
    return line


def _h_divider() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {PALETTE['sepia_border']}; border: none;")
    return line


class TracePanel(QFrame):
    """Right-hand Archival Case Ledger showing live metrics and deduction steps."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TraceContainer")
        self._steps: list[DeductionStep] = []
        self._total_sat_calls: int = 0
        self._total_cached_skips: int = 0
        self._total_decisions: int = 0
        self._total_propagations: int = 0
        self._total_backtracks: int = 0
        self._total_runtime_ms: float = 0.0

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # Ledger Header + Uniqueness Stamp
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        title = QLabel("Case Ledger & Deduction Trace")
        title.setStyleSheet(
            f"font-family: Georgia, 'Times New Roman', serif; font-size: 15px; "
            f"font-weight: 700; color: {PALETTE['ink_primary']}; background: transparent;"
        )
        top_row.addWidget(title)
        top_row.addStretch(1)

        self.uniqueness_badge = QLabel("Uniqueness: Not checked")
        self.uniqueness_badge.setStyleSheet(
            f"background-color: {PALETTE['parchment_alt']}; color: {PALETTE['ink_secondary']}; "
            f"border: 1px solid {PALETTE['sepia_border']}; border-radius: 5px; "
            f"padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )
        top_row.addWidget(self.uniqueness_badge)
        layout.addLayout(top_row)

        # Unified Ruled Ledger Strip (no floating SaaS boxes)
        ledger_band = QFrame()
        ledger_band.setStyleSheet(
            f"QFrame#LedgerBand {{ background-color: {PALETTE['parchment_alt']}; "
            f"border: 1px solid {PALETTE['sepia_border']}; border-radius: 7px; }}"
        )
        ledger_band.setObjectName("LedgerBand")
        band_vbox = QVBoxLayout(ledger_band)
        band_vbox.setContentsMargins(2, 2, 2, 2)
        band_vbox.setSpacing(0)

        self.tile_progress = _LedgerStat("SOLVED", "0 / 0")
        self.tile_vars = _LedgerStat("VARS (P + AUX)", "—")
        self.tile_clauses = _LedgerStat("CNF CLAUSES", "—")
        self.tile_sat_calls = _LedgerStat("SAT CALLS", "0")

        self.tile_decisions = _LedgerStat("DECISIONS", "0")
        self.tile_props = _LedgerStat("PROPAGATIONS", "0")
        self.tile_backtracks = _LedgerStat("BACKTRACKS", "0")
        self.tile_runtime = _LedgerStat("SAT TIME", "0.0 ms")

        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.setSpacing(0)
        for idx, stat in enumerate(
            (self.tile_progress, self.tile_vars, self.tile_clauses, self.tile_sat_calls)
        ):
            if idx > 0:
                row_top.addWidget(_v_divider())
            row_top.addWidget(stat, stretch=1)

        row_bot = QHBoxLayout()
        row_bot.setContentsMargins(0, 0, 0, 0)
        row_bot.setSpacing(0)
        for idx, stat in enumerate(
            (self.tile_decisions, self.tile_props, self.tile_backtracks, self.tile_runtime)
        ):
            if idx > 0:
                row_bot.addWidget(_v_divider())
            row_bot.addWidget(stat, stretch=1)

        band_vbox.addLayout(row_top)
        band_vbox.addWidget(_h_divider())
        band_vbox.addLayout(row_bot)
        layout.addWidget(ledger_band)

        # Trace Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Step", "Cell", "Verdict", "Result", "Clues", "SAT"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table, stretch=3)

        # Step Inspector (archival case notes)
        inspector_lbl = QLabel("Step Evidence & SAT Query Log")
        inspector_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {PALETTE['ink_secondary']}; "
            f"margin-top: 2px; background: transparent;"
        )
        layout.addWidget(inspector_lbl)

        self.inspector = QTextEdit()
        self.inspector.setObjectName("StepInspector")
        self.inspector.setReadOnly(True)
        self.inspector.setMinimumHeight(130)
        self.inspector.setPlaceholderText(
            "Select any logged step above to inspect active clues, CNF counts, and DPLL queries."
        )
        layout.addWidget(self.inspector, stretch=2)

    @property
    def step_count(self) -> int:
        return len(self._steps)

    def reset(self, state: Optional[PublicState] = None) -> None:
        """Clear all trace entries and cumulative telemetry."""
        self._steps.clear()
        self._total_sat_calls = 0
        self._total_cached_skips = 0
        self._total_decisions = 0
        self._total_propagations = 0
        self._total_backtracks = 0
        self._total_runtime_ms = 0.0

        self.table.setRowCount(0)
        self.inspector.clear()
        self.uniqueness_badge.setText("Uniqueness: Not checked")
        self.uniqueness_badge.setStyleSheet(
            f"background-color: {PALETTE['parchment_alt']}; color: {PALETTE['ink_secondary']}; "
            f"border: 1px solid {PALETTE['sepia_border']}; border-radius: 5px; "
            f"padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )

        self.tile_clauses.set_value("—")
        self.tile_sat_calls.set_value("0")
        self.tile_decisions.set_value("0")
        self.tile_props.set_value("0")
        self.tile_backtracks.set_value("0")
        self.tile_runtime.set_value("0.0 ms")

        if state is not None:
            self.update_progress(state)
            self.tile_vars.set_value(f"{state.grid_size ** 2} + 0")
        else:
            self.tile_progress.set_value("0 / 0")
            self.tile_vars.set_value("—")

    def update_progress(self, state: PublicState) -> None:
        total = len(state.characters)
        solved = len(state.revealed_cells)
        self.tile_progress.set_value(f"{solved} / {total}")

    def append_step(self, step: DeductionStep) -> None:
        """Append one `DeductionStep` from Auto Solve (or manual move) to the ledger."""
        self._steps.append(step)

        real_queries = [q for q in step.sat_queries if not q.cached]
        cached_queries = [q for q in step.sat_queries if q.cached]

        self._total_sat_calls += len(real_queries)
        self._total_cached_skips += len(cached_queries)
        for q in real_queries:
            self._total_decisions += q.metrics.decisions
            self._total_propagations += q.metrics.propagations
            self._total_backtracks += q.metrics.backtracks
            self._total_runtime_ms += q.metrics.runtime_ms

        if step.cnf_stats is not None:
            self.tile_vars.set_value(
                f"{step.cnf_stats.num_primary_vars} + {step.cnf_stats.num_aux_vars}"
            )
            self.tile_clauses.set_value(str(step.cnf_stats.num_clauses))

        sat_str = (
            f"{self._total_sat_calls} (+{self._total_cached_skips}c)"
            if self._total_cached_skips
            else str(self._total_sat_calls)
        )
        self.tile_sat_calls.set_value(sat_str)
        self.tile_decisions.set_value(str(self._total_decisions))
        self.tile_props.set_value(str(self._total_propagations))
        self.tile_backtracks.set_value(str(self._total_backtracks))
        self.tile_runtime.set_value(f"{self._total_runtime_ms:.1f} ms")

        row = self.table.rowCount()
        self.table.insertRow(row)

        verdict_str = step.verdict.value if step.verdict != Status.UNKNOWN else "—"
        cell_str = step.cell or "—"
        sat_cell_str = (
            f"{len(real_queries)}"
            + (f" (+{len(cached_queries)}c)" if cached_queries else "")
        )

        values = [
            str(step.step_number),
            cell_str,
            verdict_str,
            step.verdict_code.value,
            str(len(step.active_clue_ids)),
            sat_cell_str,
        ]
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if col == 2:
                if step.verdict == Status.CRIMINAL:
                    item.setForeground(QColor(PALETTE["criminal_badge"]))
                elif step.verdict == Status.INNOCENT:
                    item.setForeground(QColor(PALETTE["innocent_badge"]))
            elif col == 3:
                if step.verdict_code == VerdictCode.ACCEPTED:
                    item.setForeground(QColor(PALETTE["innocent_badge"]))
                elif step.verdict_code == VerdictCode.NOT_PROVABLE:
                    item.setForeground(QColor(PALETTE["ref_border"]))
                else:
                    item.setForeground(QColor(PALETTE["criminal_badge"]))
            self.table.setItem(row, col, item)

        self.table.selectRow(row)
        self.table.scrollToBottom()

    def record_manual_verdict(
        self,
        response: VerdictResponse,
        active_clue_ids: tuple[str, ...],
    ) -> None:
        """Record a manual verdict submission into the deduction ledger."""
        step = DeductionStep(
            step_number=response.public_state.step,
            active_clue_ids=active_clue_ids,
            sat_queries=(),
            cell=response.cell,
            verdict=response.submitted_status,
            verdict_code=response.code,
            revealed_clue=response.revealed_clue,
            cnf_stats=None,
        )
        self.append_step(step)

    def set_uniqueness_result(self, result: UniquenessResult) -> None:
        """Display the offline uniqueness check stamp in the ledger header."""
        status = result.solution_count_status
        if result.is_unique and status == "UNIQUE":
            self.uniqueness_badge.setText("Uniqueness: UNIQUE")
            self.uniqueness_badge.setStyleSheet(
                "background-color: #E3F0E7; color: #1C422F; border: 1px solid #3B6B52; "
                "border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )
        elif status == "UNSAT":
            self.uniqueness_badge.setText("Uniqueness: UNSAT")
            self.uniqueness_badge.setStyleSheet(
                "background-color: #FAE7E5; color: #6B191A; border: 1px solid #9E2A2B; "
                "border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )
        else:
            self.uniqueness_badge.setText("Uniqueness: MULTIPLE")
            self.uniqueness_badge.setStyleSheet(
                "background-color: #FDF1D6; color: #6B4108; border: 1px solid #C57B1A; "
                "border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )

    def _on_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if not (0 <= idx < len(self._steps)):
            return
        step = self._steps[idx]
        self.inspector.setPlainText(self._format_step_detail(step))

    @staticmethod
    def _format_step_detail(step: DeductionStep) -> str:
        lines: list[str] = [
            f"Step #{step.step_number} | Cell: {step.cell or '—'} | "
            f"Verdict: {step.verdict.value} | Result: {step.verdict_code.value}",
            f"Active Clues ({len(step.active_clue_ids)}): "
            + (", ".join(step.active_clue_ids) if step.active_clue_ids else "none"),
        ]
        if step.revealed_clue is not None:
            lines.append(
                f"Revealed Clue ({step.revealed_clue.clue_id}): "
                f"{format_clue(step.revealed_clue)}"
            )
        if step.cnf_stats is not None:
            s = step.cnf_stats
            lines.append(
                f"CNF Formula: {s.num_primary_vars} primary + {s.num_aux_vars} aux vars, "
                f"{s.num_clauses} clauses (strategy={s.encoding_strategy})"
            )
        if step.sat_queries:
            real_count = sum(1 for q in step.sat_queries if not q.cached)
            cached_count = len(step.sat_queries) - real_count
            lines.append(
                f"SAT Queries: {len(step.sat_queries)} total "
                f"({real_count} real, {cached_count} cached)"
            )
            for q in step.sat_queries[:12]:
                res = "SAT" if q.is_sat else "UNSAT"
                tag = " [cached]" if q.cached else ""
                m = q.metrics
                lines.append(
                    f"  - {q.cell} assump={list(q.assumptions)} -> {res}{tag} "
                    f"(dec={m.decisions}, prop={m.propagations}, bt={m.backtracks}, "
                    f"{m.runtime_ms:.2f}ms)"
                )
            if len(step.sat_queries) > 12:
                lines.append(f"  ... (+{len(step.sat_queries) - 12} more queries)")
        else:
            lines.append("SAT Queries: (manual verdict or pre-integration oracle)")
        return "\n".join(lines)
