"""Tactile Dossier Character Card widget for the Griductive Detective Board.

Strictly displays only `CharacterPublicInfo` (never hidden statuses or clues).
Paints a subtle brass/wax push-pin at top-center and carries a soft drop shadow
so each dossier card sits physically lifted off the cork investigation board.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)

from core.contracts.models import CellID, CharacterPublicInfo, Status
from gui.clue_formatter import format_clue
from gui.theme import PALETTE, build_card_stylesheet, pin_color_for_state


class CharacterCardWidget(QFrame):
    """Interactive dossier card representing one character cell on the board."""

    clicked = pyqtSignal(str)

    def __init__(
        self,
        cell_id: CellID,
        *,
        compact: bool = False,
        density: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CharacterCard")
        self.cell_id: CellID = cell_id
        self._density: str = density or ("compact" if compact else "normal")
        self._compact: bool = self._density == "compact"

        # Public display state (never stores hidden data)
        self._is_revealed: bool = False
        self._status: Status = Status.UNKNOWN
        self._clue_id: Optional[str] = None

        # Visual highlight flags
        self._is_selected: bool = False
        self._is_region_highlighted: bool = False
        self._is_active_clue_source: bool = False
        self._is_hint_target: bool = False
        self._is_hint_clue_source: bool = False

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if self._density == "compact":
            self.setMinimumSize(118, 108)
        elif self._density == "medium":
            self.setMinimumSize(136, 124)
        else:
            self.setMinimumSize(148, 136)

        # Soft warm offset shadow lifting card off the cork board
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(42, 31, 25, 52))
        self.setGraphicsEffect(shadow)

        self._build_ui()
        self._refresh_style()

    def _build_ui(self) -> None:
        if self._density == "compact":
            pad_x, pad_top, pad_bot, spacing = 6, 10, 5, 2
        elif self._density == "medium":
            pad_x, pad_top, pad_bot, spacing = 8, 12, 7, 3
        else:
            pad_x, pad_top, pad_bot, spacing = 11, 15, 10, 5

        layout = QVBoxLayout(self)
        layout.setContentsMargins(pad_x, pad_top, pad_x, pad_bot)
        layout.setSpacing(spacing)

        # Header row: CellID plaque + highlight pill + Status stamp
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self.coord_label = QLabel(self.cell_id)
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.coord_label)

        self.tag_label = QLabel("")
        self.tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tag_label.setVisible(False)
        header.addWidget(self.tag_label)

        header.addStretch(1)

        self.status_badge = QLabel("UNSOLVED")
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.status_badge)

        layout.addLayout(header)

        # Identity block: Editorial serif Name + warm sans Profession
        self.name_label = QLabel("")
        self.name_label.setWordWrap(False)
        layout.addWidget(self.name_label)

        self.profession_label = QLabel("")
        self.profession_label.setWordWrap(False)
        layout.addWidget(self.profession_label)

        # Clue / Sealed folder note area
        self.clue_label = QLabel("")
        self.clue_label.setWordWrap(True)
        self.clue_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.clue_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.clue_label, stretch=1)

    @property
    def is_revealed(self) -> bool:
        return self._is_revealed

    @property
    def status(self) -> Status:
        return self._status

    @property
    def clue_id(self) -> Optional[str]:
        return self._clue_id

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @property
    def is_region_highlighted(self) -> bool:
        return self._is_region_highlighted

    @property
    def is_hint_target(self) -> bool:
        return self._is_hint_target

    @property
    def is_hint_clue_source(self) -> bool:
        return self._is_hint_clue_source

    def pin_anchor_local(self) -> QPointF:
        """Center point of the top-center push-pin in local coordinates."""
        return QPointF(self.width() / 2.0, 7.5 if self._compact else 9.0)

    def update_from_public_info(self, info: CharacterPublicInfo) -> None:
        """Render strictly from immutable `CharacterPublicInfo`."""
        self.cell_id = info.cell_id
        self._is_revealed = info.is_revealed
        self._status = info.status
        self._clue_id = info.clue.clue_id if (info.is_revealed and info.clue) else None

        self.coord_label.setText(info.cell_id)
        self.name_label.setText(info.name)
        self.profession_label.setText(info.profession)

        if info.is_revealed:
            self.status_badge.setText(info.status.value)
            clue_text = format_clue(info.clue) if info.clue is not None else ""
            self.clue_label.setText(clue_text)
            self.setToolTip(
                f"{info.cell_id} — {info.name} ({info.profession})\n"
                f"Status: {info.status.value}\n"
                f"Clue ({self._clue_id}): {clue_text}\n"
                f"Click to pin & trace referenced cells."
            )
        else:
            self.status_badge.setText("UNSOLVED")
            if self._density == "compact":
                self.clue_label.setText("Face-down dossier")
            else:
                self.clue_label.setText("Face-down dossier\nClick to select & judge")
            self.setToolTip(
                f"{info.cell_id} — {info.name} ({info.profession})\n"
                f"Status: UNSOLVED (sealed face-down)\n"
                f"Click to select for CRIMINAL / INNOCENT verdict."
            )

        self._refresh_style()

    def set_highlight_flags(
        self,
        *,
        is_selected: Optional[bool] = None,
        is_region_highlighted: Optional[bool] = None,
        is_active_clue_source: Optional[bool] = None,
        is_hint_target: Optional[bool] = None,
        is_hint_clue_source: Optional[bool] = None,
    ) -> None:
        if is_selected is not None:
            self._is_selected = is_selected
        if is_region_highlighted is not None:
            self._is_region_highlighted = is_region_highlighted
        if is_active_clue_source is not None:
            self._is_active_clue_source = is_active_clue_source
        if is_hint_target is not None:
            self._is_hint_target = is_hint_target
        if is_hint_clue_source is not None:
            self._is_hint_clue_source = is_hint_clue_source
        self._refresh_style()

    def clear_highlights(self) -> None:
        self._is_selected = False
        self._is_region_highlighted = False
        self._is_active_clue_source = False
        self._is_hint_target = False
        self._is_hint_clue_source = False
        self._refresh_style()

    def _refresh_style(self) -> None:
        self.setStyleSheet(
            build_card_stylesheet(
                is_revealed=self._is_revealed,
                status=self._status,
                is_selected=self._is_selected,
                is_region_highlighted=self._is_region_highlighted,
                is_active_clue_source=self._is_active_clue_source,
                is_hint_target=self._is_hint_target,
                is_hint_clue_source=self._is_hint_clue_source,
            )
        )

        if self._density == "compact":
            name_px, prof_px, clue_px, badge_px = 12, 9, 9, 8
            clue_pad = "3px 5px"
            badge_pad = "1px 4px"
        elif self._density == "medium":
            name_px, prof_px, clue_px, badge_px = 13, 10, 10, 9
            clue_pad = "4px 6px"
            badge_pad = "1px 5px"
        else:
            name_px, prof_px, clue_px, badge_px = 15, 11, 11, 10
            clue_pad = "5px 7px"
            badge_pad = "1px 6px"

        if not self._is_revealed:
            self.coord_label.setStyleSheet(
                f"background-color: #534135; color: {PALETTE['cream_ink']}; "
                f"border-radius: 4px; padding: {badge_pad}; font-weight: 700; "
                f"font-size: {badge_px}px; font-family: Consolas, monospace;"
            )
            self.status_badge.setStyleSheet(
                f"background-color: #4D3D32; color: #D8CAB6; border: 1px solid #695445; "
                f"border-radius: 4px; padding: {badge_pad}; font-weight: 700; font-size: {badge_px}px;"
            )
            self.name_label.setStyleSheet(
                f"color: {PALETTE['sealed_text']}; font-family: Georgia, 'Times New Roman', serif; "
                f"font-weight: 700; font-size: {name_px}px; background: transparent;"
            )
            self.profession_label.setStyleSheet(
                f"color: {PALETTE['sealed_subtext']}; font-size: {prof_px}px; background: transparent;"
            )
            self.clue_label.setStyleSheet(
                f"background-color: {PALETTE['sealed_inner']}; color: #B9A894; "
                f"border: 1px dashed #634F40; border-radius: 5px; "
                f"padding: {clue_pad}; font-style: italic; font-size: {clue_px}px;"
            )
        else:
            badge_bg = (
                PALETTE["criminal_badge"]
                if self._status == Status.CRIMINAL
                else PALETTE["innocent_badge"]
            )
            clue_border = (
                "#E5C4BE" if self._status == Status.CRIMINAL else "#C4D6C8"
            )
            if self._is_region_highlighted:
                clue_border = "#DFB36B"
            elif self._is_hint_clue_source:
                clue_border = "#C9A7CE"

            self.coord_label.setStyleSheet(
                f"background-color: #E9DEC9; color: {PALETTE['ink_primary']}; "
                f"border: 1px solid #CDBB9F; border-radius: 4px; padding: {badge_pad}; "
                f"font-weight: 700; font-size: {badge_px}px; font-family: Consolas, monospace;"
            )
            self.status_badge.setStyleSheet(
                f"background-color: {badge_bg}; color: #FAF6F0; border-radius: 4px; "
                f"padding: {badge_pad}; font-weight: 700; font-size: {badge_px}px; "
                f"letter-spacing: 0.3px;"
            )
            self.name_label.setStyleSheet(
                f"color: {PALETTE['ink_primary']}; font-family: Georgia, 'Times New Roman', serif; "
                f"font-weight: 700; font-size: {name_px}px; background: transparent;"
            )
            self.profession_label.setStyleSheet(
                f"color: {PALETTE['ink_secondary']}; font-size: {prof_px}px; background: transparent;"
            )
            self.clue_label.setStyleSheet(
                f"background-color: rgba(255, 253, 248, 0.88); color: {PALETTE['ink_primary']}; "
                f"border: 1px solid {clue_border}; border-radius: 5px; "
                f"padding: {clue_pad}; font-size: {clue_px}px;"
            )

        # Dynamic semantic pill
        tag_text, tag_bg = "", ""
        if self._is_hint_target:
            tag_text, tag_bg = "HINT", PALETTE["hint_border"]
        elif self._is_hint_clue_source:
            tag_text, tag_bg = "CLUE", PALETTE["hint_border"]
        elif self._is_active_clue_source:
            tag_text, tag_bg = ("PIN" if self._density == "compact" else "ACTIVE"), PALETTE["active_clue_border"]
        elif self._is_region_highlighted:
            tag_text, tag_bg = "REF", PALETTE["ref_border"]
        elif self._is_selected:
            tag_text, tag_bg = "SEL", PALETTE["brass_deep"]

        if tag_text:
            self.tag_label.setText(tag_text)
            self.tag_label.setStyleSheet(
                f"background-color: {tag_bg}; color: #FDF8F0; border-radius: 4px; "
                f"padding: {badge_pad}; font-weight: 700; font-size: {badge_px}px;"
            )
            self.tag_label.setVisible(True)
        else:
            self.tag_label.setVisible(False)

        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = self.pin_anchor_local()
        radius = 3.8 if self._compact else 4.6
        outer_hex, hi_hex = pin_color_for_state(
            is_revealed=self._is_revealed,
            status=self._status,
            is_selected=self._is_selected,
            is_region_highlighted=self._is_region_highlighted,
            is_active_clue_source=self._is_active_clue_source,
            is_hint_target=self._is_hint_target,
            is_hint_clue_source=self._is_hint_clue_source,
        )

        # Soft pin shadow on card paper
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 20, 14, 70))
        painter.drawEllipse(QPointF(center.x() + 1.0, center.y() + 1.4), radius, radius)

        # Pin head
        painter.setBrush(QColor(outer_hex))
        painter.setPen(QPen(QColor(42, 31, 25, 130), 0.9))
        painter.drawEllipse(center, radius, radius)

        # Tiny specular brass/wax glint
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(hi_hex))
        painter.drawEllipse(
            QPointF(center.x() - radius * 0.3, center.y() - radius * 0.3),
            radius * 0.34,
            radius * 0.34,
        )
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cell_id)
        super().mousePressEvent(event)
