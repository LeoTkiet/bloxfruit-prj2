"""Game Engine, Puzzle Loader, and Puzzle Validator package (owned by TV1)."""

from engine.game_engine import GameEngine
from engine.puzzle_loader import (
    HiddenCharacter,
    PuzzleDefinition,
    PuzzleLoadError,
    load_puzzle_definition,
    parse_clue,
    parse_region_spec,
)
from engine.puzzle_validator import (
    PuzzleValidationError,
    extract_clue_referenced_cells,
    resolve_region_cells,
    validate_clue,
    validate_puzzle,
    validate_region,
)

__all__ = [
    "GameEngine",
    "HiddenCharacter",
    "PuzzleDefinition",
    "PuzzleLoadError",
    "PuzzleValidationError",
    "load_puzzle_definition",
    "parse_clue",
    "parse_region_spec",
    "resolve_region_cells",
    "extract_clue_referenced_cells",
    "validate_region",
    "validate_clue",
    "validate_puzzle",
]
