"""Warm Classic Detective Board visual theme & QSS system for Griductive Solver.

Palette philosophy ("The Archival Case Board"):
- Deep espresso walnut chrome frames a warm cork-linen investigation mat.
- Cards behave like tactile manila & parchment case dossiers pinned to the board.
- Semantic states harmonize inside one warm archival family:
  wax-seal crimson (CRIMINAL), botanical sage (INNOCENT), smoked umber (SEALED),
  burnished brass (SELECTED / REF), Prussian fountain ink (ACTIVE CLUE),
  and archival plum (HINT).
"""

from __future__ import annotations

from core.contracts.models import Status

PALETTE: dict[str, str] = {
    # Surfaces & Grounds
    "walnut_deep": "#2A1F19",       # Masthead header bar
    "walnut_mid": "#3D2E25",        # Toolbar controls / accents on dark rail
    "walnut_border": "#574335",     # Brass-tinted dark border
    "linen_canvas": "#EAE1D2",      # Main window warm linen ground
    "cork_mat": "#DCCEB7",          # Investigation board surface
    "cork_frame": "#B49B7A",        # Board wood-trim border
    "cork_gridline": "#CBB99D",     # Subtle drafted mat gridlines
    "parchment": "#FAF5EB",         # Ledger / panel warm cream paper
    "parchment_alt": "#F3EBDC",     # Alternate row / subtle recessed tint
    "sepia_border": "#D5C6AE",      # Panel & ledger hairline rules
    "sepia_border_strong": "#B7A286",
    # Typography
    "ink_primary": "#231A14",       # Deep sepia-charcoal ink (>=12:1 on parchment)
    "ink_secondary": "#57473B",     # Secondary warm umber ink (>=6.5:1)
    "ink_muted": "#756354",         # Muted archival label (>=4.6:1 on parchment)
    "cream_ink": "#F7EFE2",         # Primary text on espresso walnut
    "cream_sub": "#CCBFA9",         # Secondary text on espresso walnut
    # Card States
    "sealed_bg": "#3A2D25",         # Face-down dossier folder
    "sealed_bg_hover": "#46372D",
    "sealed_border": "#5E4B3E",
    "sealed_inner": "#2E231C",
    "sealed_text": "#F5EDE0",
    "sealed_subtext": "#CBBCA6",
    "criminal_bg": "#FCF2EE",       # Warm blush parchment
    "criminal_border": "#9E2A2B",   # Wax-seal crimson
    "criminal_badge": "#9E2A2B",
    "criminal_ink": "#6E1A1B",
    "innocent_bg": "#F2F6F0",       # Warm sage parchment
    "innocent_border": "#3B6B52",   # Botanical archival sage
    "innocent_badge": "#2F5C45",
    "innocent_ink": "#1F4230",
    # Interactive Highlights & Pins
    "brass": "#C58A2B",             # Selected card & brass accents
    "brass_deep": "#9A6719",
    "brass_glow_dark": "#4E3A25",   # Selected face-down tint
    "ref_border": "#C57B1A",        # Highlighted clue region
    "ref_bg_light": "#FDF2D6",      # Honey parchment highlight on revealed card
    "ref_bg_dark": "#563D1F",       # Warm amber-umber highlight on face-down card
    "ref_string": "#B83B2E",        # Classic red detective investigation twine
    "active_clue_border": "#27586E",# Prussian fountain-pen ink
    "hint_border": "#6F3D73",       # Archival plum wax
    "hint_target_bg": "#45284A",    # Face-down hint target surface
    "hint_clue_bg": "#F5ECF6",      # Revealed hint clue tint
    "hint_string": "#6F3D73",       # Plum hint connection twine
}

BANNER_STYLES: dict[str, tuple[str, str, str]] = {
    # kind -> (background, border, text)
    "INFO": ("#F5EEE2", "#C4B094", "#3B2D23"),
    "ACCEPTED": ("#E9F2EB", "#3B6B52", "#1C422F"),
    "SOLVED": ("#DFEFE4", "#2F5C45", "#173827"),
    "NOT_PROVABLE": ("#FDF1D6", "#C57B1A", "#6B4108"),
    "AMBIGUOUS": ("#FBE6D4", "#B8551E", "#6E2E0D"),
    "CONTRADICTED": ("#FAE7E5", "#9E2A2B", "#6B191A"),
    "INCONSISTENT": ("#4E181A", "#9E2A2B", "#FCF2EE"),
    "HINT": ("#F4EBF6", "#6F3D73", "#431E47"),
}


APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {PALETTE['linen_canvas']};
}}
QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: {PALETTE['ink_primary']};
}}
QStatusBar {{
    background-color: {PALETTE['walnut_deep']};
    color: {PALETTE['cream_sub']};
    border-top: 1px solid {PALETTE['walnut_border']};
    font-size: 11px;
    padding: 2px 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* Espresso Walnut Top Masthead Bar */
QFrame#TopBar {{
    background-color: {PALETTE['walnut_deep']};
    border: 1px solid {PALETTE['walnut_border']};
    border-radius: 10px;
}}
QFrame#TopBar QLabel {{
    color: {PALETTE['cream_ink']};
    background: transparent;
}}
QFrame#TopBar QComboBox {{
    background-color: {PALETTE['walnut_mid']};
    color: {PALETTE['cream_ink']};
    border: 1px solid {PALETTE['walnut_border']};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    min-height: 22px;
}}
QFrame#TopBar QComboBox:hover {{
    border-color: {PALETTE['brass']};
}}
QFrame#TopBar QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QFrame#TopBar QComboBox QAbstractItemView {{
    background-color: {PALETTE['parchment']};
    color: {PALETTE['ink_primary']};
    border: 1px solid {PALETTE['sepia_border_strong']};
    selection-background-color: #E8D9C0;
    selection-color: {PALETTE['ink_primary']};
    outline: none;
}}
QFrame#TopBar QPushButton {{
    background-color: {PALETTE['walnut_mid']};
    color: {PALETTE['cream_ink']};
    border: 1px solid {PALETTE['walnut_border']};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}}
QFrame#TopBar QPushButton:hover {{
    background-color: #4D3B30;
    border-color: {PALETTE['brass']};
}}
QFrame#TopBar QPushButton:pressed {{
    background-color: #241A15;
}}
QFrame#TopBar QPushButton:disabled {{
    background-color: #312620;
    color: #7D6D60;
    border-color: #42342C;
}}
QFrame#TopBar QPushButton#PrimaryBtn {{
    background-color: {PALETTE['brass']};
    color: #1F150C;
    border: 1px solid #D9A246;
    font-weight: 700;
}}
QFrame#TopBar QPushButton#PrimaryBtn:hover {{
    background-color: #D49836;
}}
QFrame#TopBar QPushButton#PrimaryBtn:disabled {{
    background-color: #6B5639;
    color: #B5A38C;
    border-color: #6B5639;
}}
QFrame#TopBar QPushButton#HintBtn {{
    background-color: {PALETTE['hint_border']};
    color: #FAF4FB;
    border: 1px solid #8A538F;
}}
QFrame#TopBar QPushButton#HintBtn:hover {{
    background-color: #824987;
}}
QFrame#TopBar QPushButton#HintBtn:disabled {{
    background-color: #4E3B50;
    color: #A896AA;
    border-color: #4E3B50;
}}
QFrame#TopBar QPushButton#DangerBtn {{
    background-color: #B8551E;
    color: #FFF8F2;
    border: 1px solid #D46A2E;
    font-weight: 700;
}}
QFrame#TopBar QPushButton#DangerBtn:hover {{
    background-color: #CE6024;
}}

/* Cork Investigation Board Frame & Warm Parchment Action/Ledger Panels */
QFrame#BoardContainer {{
    background-color: {PALETTE['cork_mat']};
    border: 2px solid {PALETTE['cork_frame']};
    border-radius: 10px;
}}
QFrame#ActionBar, QFrame#TraceContainer {{
    background-color: {PALETTE['parchment']};
    border: 1px solid {PALETTE['sepia_border']};
    border-radius: 10px;
}}

/* General Buttons (Action Bar) */
QPushButton {{
    background-color: {PALETTE['parchment_alt']};
    color: {PALETTE['ink_primary']};
    border: 1px solid {PALETTE['sepia_border_strong']};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: #E9DEC9;
    border-color: {PALETTE['brass_deep']};
}}
QPushButton:pressed {{
    background-color: #DFD1B8;
}}
QPushButton:disabled {{
    background-color: #EFE8DC;
    color: #A49583;
    border-color: #DDD2C1;
}}
QPushButton#CriminalBtn {{
    background-color: {PALETTE['criminal_badge']};
    color: #FDF7F2;
    border: 1px solid #7E1E1F;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton#CriminalBtn:hover {{
    background-color: #872223;
}}
QPushButton#CriminalBtn:disabled {{
    background-color: #DEC3BF;
    color: #FAF4F2;
    border-color: #D2B2AE;
}}
QPushButton#InnocentBtn {{
    background-color: {PALETTE['innocent_badge']};
    color: #F4FAF6;
    border: 1px solid #224634;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton#InnocentBtn:hover {{
    background-color: #254C38;
}}
QPushButton#InnocentBtn:disabled {{
    background-color: #C3D4C9;
    color: #F7FAF8;
    border-color: #B4C8BB;
}}

/* Splitter handle */
QSplitter::handle {{
    background-color: transparent;
}}
QSplitter::handle:hover {{
    background-color: {PALETTE['cork_frame']};
    border-radius: 3px;
}}

/* Ledger Table */
QTableWidget {{
    background-color: {PALETTE['parchment']};
    alternate-background-color: {PALETTE['parchment_alt']};
    border: 1px solid {PALETTE['sepia_border']};
    border-radius: 6px;
    gridline-color: #E7DCCB;
    font-size: 11px;
    color: {PALETTE['ink_primary']};
    selection-background-color: #E5D4B7;
    selection-color: {PALETTE['ink_primary']};
}}
QTableWidget::item {{
    padding: 3px 4px;
}}
QHeaderView::section {{
    background-color: #EFE5D3;
    color: {PALETTE['ink_secondary']};
    border: none;
    border-bottom: 1px solid {PALETTE['sepia_border_strong']};
    padding: 5px 6px;
    font-weight: 700;
    font-size: 11px;
}}

/* Typewriter Step Inspector */
QTextEdit#StepInspector {{
    background-color: #F5EEE0;
    border: 1px solid {PALETTE['sepia_border']};
    border-radius: 6px;
    font-family: "Consolas", "Cascadia Code", monospace;
    font-size: 11px;
    color: {PALETTE['ink_primary']};
    padding: 6px;
    selection-background-color: #DEC8A3;
    selection-color: {PALETTE['ink_primary']};
}}

/* Archival Scrollbars (no default cold grey Qt scrollbars) */
QScrollBar:vertical {{
    background: {PALETTE['parchment_alt']};
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #C4B094;
    min-height: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A68D6B;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {PALETTE['parchment_alt']};
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #C4B094;
    min-width: 24px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #A68D6B;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def build_banner_stylesheet(kind: str) -> str:
    """Return QSS for the case feedback banner."""
    bg, border, fg = BANNER_STYLES.get(kind, BANNER_STYLES["INFO"])
    return (
        f"QLabel#FeedbackBanner {{"
        f"  background-color: {bg};"
        f"  border: 1.5px solid {border};"
        f"  border-radius: 8px;"
        f"  color: {fg};"
        f"  padding: 8px 14px;"
        f"  font-weight: 600;"
        f"  font-size: 12px;"
        f"}}"
    )


def build_card_stylesheet(
    *,
    is_revealed: bool,
    status: Status,
    is_selected: bool,
    is_region_highlighted: bool,
    is_active_clue_source: bool,
    is_hint_target: bool,
    is_hint_clue_source: bool,
) -> str:
    """Compute harmonious dossier card surface & border QSS."""
    border_width = 2

    if not is_revealed:
        bg = PALETTE["sealed_bg"]
        border = PALETTE["sealed_border"]
        if is_hint_target:
            bg = PALETTE["hint_target_bg"]
            border = PALETTE["hint_border"]
            border_width = 3
        elif is_selected:
            bg = PALETTE["brass_glow_dark"]
            border = PALETTE["brass"]
            border_width = 3
        elif is_region_highlighted:
            bg = PALETTE["ref_bg_dark"]
            border = PALETTE["ref_border"]
            border_width = 3
    else:
        if status == Status.CRIMINAL:
            bg = PALETTE["criminal_bg"]
            border = PALETTE["criminal_border"]
        else:
            bg = PALETTE["innocent_bg"]
            border = PALETTE["innocent_border"]

        if is_hint_clue_source:
            bg = PALETTE["hint_clue_bg"]
            border = PALETTE["hint_border"]
            border_width = 3
        elif is_active_clue_source:
            border = PALETTE["active_clue_border"]
            border_width = 3
        elif is_region_highlighted:
            bg = PALETTE["ref_bg_light"]
            border = PALETTE["ref_border"]
            border_width = 3

    return (
        f"QFrame#CharacterCard {{"
        f"  background-color: {bg};"
        f"  border: {border_width}px solid {border};"
        f"  border-radius: 8px;"
        f"}}"
    )


def pin_color_for_state(
    *,
    is_revealed: bool,
    status: Status,
    is_selected: bool,
    is_region_highlighted: bool,
    is_active_clue_source: bool,
    is_hint_target: bool,
    is_hint_clue_source: bool,
) -> tuple[str, str]:
    """Return `(outer_hex, highlight_hex)` for the painted brass/wax push-pin."""
    if is_hint_target or is_hint_clue_source:
        return ("#7E4582", "#D7B2DA")
    if is_active_clue_source:
        return ("#27586E", "#8AC0D9")
    if is_region_highlighted:
        return ("#C57B1A", "#FCE0A2")
    if is_selected:
        return ("#D49A34", "#FFF0C2")
    if is_revealed:
        if status == Status.CRIMINAL:
            return ("#A42B2C", "#F09B9B")
        return ("#35694E", "#9ED4B6")
    return ("#B38B45", "#EFE0B9")
