"""Unit tests for `Source/main.py` CLI parsing and Dependency Injection wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.contracts.interfaces import IGameEngine, ILogicAgent
from main import parse_args, wire_system


def test_parse_args_defaults_and_overrides() -> None:
    defaults = parse_args([])
    assert defaults.puzzle is None
    assert defaults.encoding == "direct"
    assert defaults.heuristic == "moms"
    assert defaults.no_pure_literal is False
    assert defaults.no_model_cache is False
    assert defaults.strict is False

    custom = parse_args(
        [
            "--puzzle",
            "Source/puzzles/3x3/3x3_01_precinct_basics.json",
            "--encoding",
            "sinz",
            "--heuristic",
            "jw",
            "--no-pure-literal",
            "--no-model-cache",
            "--strict",
        ]
    )
    assert custom.puzzle == Path("Source/puzzles/3x3/3x3_01_precinct_basics.json")
    assert custom.encoding == "sinz"
    assert custom.heuristic == "jw"
    assert custom.no_pure_literal is True
    assert custom.no_model_cache is True
    assert custom.strict is True


def test_wire_system_returns_contract_compliant_engine_and_agent() -> None:
    engine, agent, mode_desc = wire_system(strict=False)
    assert isinstance(engine, IGameEngine)
    assert isinstance(agent, ILogicAgent)
    assert mode_desc != ""


def test_wire_system_strict_uses_full_production_stack() -> None:
    """Guarantees `wire_system(strict=True)` connects real TV1–TV4 modules with no fallback."""
    engine, agent, mode_desc = wire_system(strict=True)
    assert isinstance(engine, IGameEngine)
    assert isinstance(agent, ILogicAgent)
    assert "Production stack" in mode_desc
    assert "CNFEncoder" in mode_desc
    assert "DPLLSolver" in mode_desc
    assert "DeductiveLogicAgent" in mode_desc

    # End-to-end smoke solve on a real puzzle with the full production stack
    puzzle_path = (
        Path(__file__).resolve().parent.parent.parent
        / "puzzles"
        / "3x3"
        / "3x3_01_precinct_basics.json"
    )
    engine.load_puzzle(puzzle_path)
    steps = agent.run_auto_solve(engine)
    assert engine.get_public_state().is_solved is True
    assert len(steps) == 7
    assert any(
        (not q.cached) for step in steps for q in step.sat_queries
    )
