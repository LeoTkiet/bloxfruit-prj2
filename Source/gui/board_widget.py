"""N x N Detective Investigation Board widget with pin-to-pin clue string overlay.

Signature visual move: when a revealed clue is clicked (or Hint highlights supporting
clues), thin anti-aliased detective strings curve softly from the source pin(s) to
their referenced target pins without blocking mouse interaction.
"""

from __future__ import annotations

from typing import Optional, Sequence

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

from core.contracts.models import (
    CellID,
    PublicState,
    col_index_to_letter,
    coords_to_cell_id,
)
from gui.card_widget import CharacterCardWidget
from gui.theme import PALETTE


class _DetectiveStringOverlay(QWidget):
    """Mouse-transparent overlay painting curved investigation twine between pins."""

    def __init__(self, board: "BoardWidget") -> None:
        super().__init__(board)
        self._board = board
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event: QPaintEvent) -> None:
        pairs, color_hex = self._board._active_string_links()
        if not pairs:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        base_color = QColor(color_hex)
        shadow_pen = QPen(QColor(42, 31, 25, 48), 2.8, Qt.PenStyle.SolidLine)
        shadow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        twine_color = QColor(base_color)
        twine_color.setAlpha(205)
        twine_pen = QPen(twine_color, 1.9, Qt.PenStyle.SolidLine)
        twine_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        for src_id, dst_id in pairs:
            if src_id == dst_id:
                continue
            p1 = self._board._card_pin_in_board(src_id)
            p2 = self._board._card_pin_in_board(dst_id)
            if p1 is None or p2 is None:
                continue

            # Natural slight catenary sag like string pinned on a cork board
            mid_x = (p1.x() + p2.x()) / 2.0
            dist = ((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2) ** 0.5
            sag = min(28.0, max(10.0, dist * 0.08))
            ctrl = QPointF(mid_x, (p1.y() + p2.y()) / 2.0 + sag)

            shadow_path = QPainterPath(QPointF(p1.x(), p1.y() + 2.0))
            shadow_path.quadTo(QPointF(ctrl.x(), ctrl.y() + 2.5), QPointF(p2.x(), p2.y() + 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(shadow_pen)
            painter.drawPath(shadow_path)

            path = QPainterPath(p1)
            path.quadTo(ctrl, p2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(twine_pen)
            painter.drawPath(path)

            # Small brass knot rings at anchor points
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base_color)
            painter.drawEllipse(p1, 3.0, 3.0)
            painter.drawEllipse(p2, 3.0, 3.0)

        painter.end()


class BoardWidget(QWidget):
    """Displays an N x N (N in {3, 4, 5}) investigation grid of dossier cards."""

    cell_clicked = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grid_size: int = 0
        self._cards: dict[CellID, CharacterCardWidget] = {}
        self._selected_cell: Optional[CellID] = None
        self._active_clue_source: Optional[CellID] = None
        self._highlighted_cells: set[CellID] = set()
        self._hint_target: Optional[CellID] = None
        self._hint_clue_owners: set[CellID] = set()

        self._grid_layout = QGridLayout(self)
        self._grid_layout.setContentsMargins(8, 8, 10, 10)
        self._grid_layout.setSpacing(10)

        self._overlay = _DetectiveStringOverlay(self)
        self._overlay.raise_()

    @property
    def grid_size(self) -> int:
        return self._grid_size

    @property
    def selected_cell(self) -> Optional[CellID]:
        return self._selected_cell

    @property
    def active_clue_source(self) -> Optional[CellID]:
        return self._active_clue_source

    @property
    def highlighted_cells(self) -> frozenset[CellID]:
        return frozenset(self._highlighted_cells)

    def get_card(self, cell_id: CellID) -> CharacterCardWidget:
        return self._cards[cell_id]

    def _card_pin_in_board(self, cell_id: CellID) -> Optional[QPointF]:
        card = self._cards.get(cell_id)
        if card is None or not card.isVisible():
            return None
        local_pt = card.pin_anchor_local().toPoint()
        mapped = card.mapTo(self, local_pt)
        return QPointF(mapped)

    def _active_string_links(self) -> tuple[list[tuple[CellID, CellID]], str]:
        if self._active_clue_source and self._highlighted_cells:
            return (
                [(self._active_clue_source, dst) for dst in sorted(self._highlighted_cells)],
                PALETTE["ref_string"],
            )
        if self._hint_target and self._hint_clue_owners:
            return (
                [(src, self._hint_target) for src in sorted(self._hint_clue_owners)],
                PALETTE["hint_string"],
            )
        return ([], PALETTE["ref_string"])

    def _clear_layout(self) -> None:
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()

    def _rebuild_grid(self, grid_size: int) -> None:
        self._clear_layout()
        self._grid_size = grid_size
        density = "compact" if grid_size >= 5 else ("medium" if grid_size == 4 else "normal")
        self._grid_layout.setSpacing(6 if grid_size >= 5 else (8 if grid_size == 4 else 11))

        for idx in range(7):
            self._grid_layout.setRowStretch(idx, 0)
            self._grid_layout.setColumnStretch(idx, 0)

        plaque_style = (
            f"background-color: #EFE5D3; color: {PALETTE['ink_secondary']}; "
            f"border: 1px solid {PALETTE['cork_frame']}; border-radius: 4px; "
            f"font-weight: 800; font-size: 11px; font-family: Consolas, monospace; "
            f"padding: 1px 4px;"
        )

        corner = QLabel("")
        corner.setFixedSize(26, 22)
        self._grid_layout.addWidget(corner, 0, 0)

        for col_idx in range(grid_size):
            col_lbl = QLabel(col_index_to_letter(col_idx))
            col_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_lbl.setStyleSheet(plaque_style)
            col_lbl.setFixedHeight(22)
            self._grid_layout.addWidget(col_lbl, 0, col_idx + 1)
            self._grid_layout.setColumnStretch(col_idx + 1, 1)

        for row_idx in range(grid_size):
            row_lbl = QLabel(str(row_idx + 1))
            row_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_lbl.setStyleSheet(plaque_style)
            row_lbl.setFixedWidth(26)
            self._grid_layout.addWidget(row_lbl, row_idx + 1, 0)
            self._grid_layout.setRowStretch(row_idx + 1, 1)

            for col_idx in range(grid_size):
                cid = coords_to_cell_id(row_idx, col_idx)
                card = CharacterCardWidget(
                    cid,
                    compact=(density == "compact"),
                    density=density,
                    parent=self,
                )
                card.clicked.connect(self.cell_clicked.emit)
                self._cards[cid] = card
                self._grid_layout.addWidget(card, row_idx + 1, col_idx + 1)

        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()
        self._overlay.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        # Subtle drafted cork-mat crosshair dots to evoke a classic evidence board
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PALETTE["cork_gridline"]))
        step = 24
        w, h = self.width(), self.height()
        for y in range(12, h, step):
            for x in range(12, w, step):
                painter.drawRect(x, y, 2, 2)
        painter.end()

    def render_state(self, state: PublicState) -> None:
        """Update board layout and every card from an immutable `PublicState`."""
        if state.grid_size != self._grid_size:
            self._rebuild_grid(state.grid_size)
            self._reset_highlight_state()

        for info in state.characters:
            card = self._cards[info.cell_id]
            card.update_from_public_info(info)

        if self._selected_cell is not None:
            sel_card = self._cards.get(self._selected_cell)
            if sel_card is None or sel_card.is_revealed:
                self._selected_cell = None

        self._apply_all_highlights()

    def set_selected_cell(self, cell_id: Optional[CellID]) -> None:
        self._selected_cell = cell_id
        self._apply_all_highlights()

    def set_clue_highlight(
        self,
        source_cell: Optional[CellID],
        highlighted_cells: Sequence[CellID],
    ) -> None:
        self._active_clue_source = source_cell
        self._highlighted_cells = set(highlighted_cells)
        self._hint_target = None
        self._hint_clue_owners.clear()
        self._apply_all_highlights()

    def set_hint_highlight(
        self,
        target_cell: Optional[CellID],
        clue_owner_cells: Sequence[CellID],
    ) -> None:
        self._active_clue_source = None
        self._highlighted_cells.clear()
        self._hint_target = target_cell
        self._hint_clue_owners = set(clue_owner_cells)
        if target_cell is not None:
            self._selected_cell = target_cell
        self._apply_all_highlights()

    def clear_highlights(self) -> None:
        self._reset_highlight_state()
        self._apply_all_highlights()

    def _reset_highlight_state(self) -> None:
        self._selected_cell = None
        self._active_clue_source = None
        self._highlighted_cells.clear()
        self._hint_target = None
        self._hint_clue_owners.clear()

    def _apply_all_highlights(self) -> None:
        for cid, card in self._cards.items():
            card.set_highlight_flags(
                is_selected=(cid == self._selected_cell),
                is_region_highlighted=(cid in self._highlighted_cells),
                is_active_clue_source=(cid == self._active_clue_source),
                is_hint_target=(cid == self._hint_target),
                is_hint_clue_source=(cid in self._hint_clue_owners),
            )
        self._overlay.setGeometry(self.rect())
        self._overlay.raise_()
        self._overlay.update()
