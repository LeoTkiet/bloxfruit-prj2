"""Main entry point & Dependency Injection container for Griductive Solver (TV5).

Supports launching from either `Source/` (`python main.py`) or the repository
root (`python Source/main.py`).

Wires all five team modules together exclusively through their shared contracts:
- TV1 (`engine/`): `GameEngine`
- TV2 (`logic/`): `CNFEncoder`
- TV3 (`solver/`): `DPLLSolver`, `DPLLConfig`
- TV4 (`agent/`): `DeductiveLogicAgent`
- TV5 (`gui/`): `MainWindow`
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from typing import Optional

# Ensure `Source/` is on sys.path regardless of working directory
SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from core.contracts.interfaces import IGameEngine, ILogicAgent
from engine.game_engine import GameEngine

PUZZLES_DIR = SOURCE_DIR / "puzzles"


def wire_system(
    *,
    encoding: str = "direct",
    heuristic: str = "moms",
    enable_pure_literal: bool = True,
    use_model_cache: bool = True,
    strict: bool = False,
) -> tuple[IGameEngine, ILogicAgent, str]:
    """Assemble the complete Griductive Solver pipeline via Dependency Injection.

    Returns:
        `(engine, agent, mode_description)` where `mode_description` indicates
        whether the full production CNF+DPLL+Agent stack is active.
    """
    try:
        from agent.logic_agent import DeductiveLogicAgent
        from logic.cnf_encoder import CNFEncoder
        from solver.dpll_solver import DPLLSolver
        from solver.heuristics import DPLLConfig

        encoder = CNFEncoder(cardinality_encoding=encoding)
        solver = DPLLSolver(
            config=DPLLConfig(
                heuristic=heuristic,  # type: ignore[arg-type]
                enable_pure_literal=enable_pure_literal,
            )
        )
        agent: ILogicAgent = DeductiveLogicAgent(
            encoder=encoder,
            solver=solver,
            use_model_cache=use_model_cache,
        )
        engine: IGameEngine = GameEngine(logic_agent=agent, encoder=encoder)
        mode = (
            f"Production stack: CNFEncoder({encoding}) + "
            f"DPLLSolver({heuristic}, pure_literal={enable_pure_literal}) + "
            f"DeductiveLogicAgent(model_cache={use_model_cache})"
        )
        return engine, agent, mode
    except ImportError as exc:
        if strict:
            raise ImportError(
                "Strict mode requires all modules (TV1 engine, TV2 logic, "
                f"TV3 solver, TV4 agent) to be present: {exc}"
            ) from exc

        # Pre-integration branch fallback (when TV2/TV4 are not yet merged into dev)
        from tests.test_engine.mock_agent import ExactTestOracleAgent

        warnings.warn(
            f"Full CNF/Agent modules not yet merged ({exc}); falling back to "
            "ExactTestOracleAgent for pre-integration GUI preview.",
            RuntimeWarning,
            stacklevel=2,
        )
        fallback_agent: ILogicAgent = ExactTestOracleAgent()
        fallback_engine: IGameEngine = GameEngine(logic_agent=fallback_agent)
        return fallback_engine, fallback_agent, "Pre-integration fallback (ExactTestOracleAgent)"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Griductive Solver — No-Guess Propositional Logic AI GUI"
    )
    parser.add_argument(
        "--puzzle",
        type=Path,
        default=None,
        help="Optional path to a puzzle JSON file to load on startup.",
    )
    parser.add_argument(
        "--encoding",
        choices=("direct", "sinz"),
        default="direct",
        help="Cardinality CNF encoding strategy for TV2's CNFEncoder (default: direct).",
    )
    parser.add_argument(
        "--heuristic",
        choices=("lexicographic", "moms", "jw"),
        default="moms",
        help="DPLL branching heuristic for TV3's DPLLSolver (default: moms).",
    )
    parser.add_argument(
        "--no-pure-literal",
        action="store_true",
        help="Disable Pure-Literal Elimination in DPLLSolver.",
    )
    parser.add_argument(
        "--no-model-cache",
        action="store_true",
        help="Disable Model Caching in DeductiveLogicAgent.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if any production module (TV1–TV4) is missing.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Launch the Griductive Solver PyQt6 desktop application."""
    args = parse_args(argv)

    from PyQt6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    engine, agent, mode_desc = wire_system(
        encoding=args.encoding,
        heuristic=args.heuristic,
        enable_pure_literal=not args.no_pure_literal,
        use_model_cache=not args.no_model_cache,
        strict=args.strict,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Griductive Solver")

    initial_puzzle: Optional[Path] = args.puzzle
    if initial_puzzle is not None and not initial_puzzle.is_absolute():
        initial_puzzle = initial_puzzle.resolve()

    window = MainWindow(
        engine=engine,
        agent=agent,
        puzzles_dir=PUZZLES_DIR,
        initial_puzzle=initial_puzzle,
    )
    window.statusBar().showMessage(mode_desc)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
