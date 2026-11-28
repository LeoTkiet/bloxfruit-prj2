"""PyQt6 desktop GUI package for Griductive Solver (owned by TV5)."""

from __future__ import annotations

from gui.board_widget import BoardWidget
from gui.card_widget import CharacterCardWidget
from gui.clue_formatter import format_clue, format_region
from gui.main_window import MainWindow, discover_puzzle_files
from gui.trace_panel import TracePanel
from gui.worker import AutoSolveWorker

__all__ = [
    "AutoSolveWorker",
    "BoardWidget",
    "CharacterCardWidget",
    "MainWindow",
    "TracePanel",
    "discover_puzzle_files",
    "format_clue",
    "format_region",
]
