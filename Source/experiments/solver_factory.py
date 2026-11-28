"""Factory resolving TV3's real DPLL solver with a safe StubDPLLSolver fallback.

Mirrors `encoder_factory`: when `solver.DPLLSolver` exists (after TV3's PR is
merged into `dev`) it is used with the requested heuristic / pure-literal flags;
otherwise a warning is emitted and the deterministic TV4 stub is returned.
"""

from __future__ import annotations

import warnings

from core.contracts.interfaces import ISATSolver
from experiments.stub_solver import StubDPLLSolver

try:  # TV3 (`solver/`) may not be merged yet on this branch.
    from solver import DPLLConfig, DPLLSolver  # type: ignore[attr-defined]

    REAL_SOLVER_AVAILABLE = True
except ImportError:
    DPLLConfig = None  # type: ignore[assignment,misc]
    DPLLSolver = None  # type: ignore[assignment,misc]
    REAL_SOLVER_AVAILABLE = False


def make_solver(heuristic: str = "lexicographic", pure_literal: bool = False) -> ISATSolver:
    """Return TV3's `DPLLSolver` configured as requested, or `StubDPLLSolver` if absent."""
    if REAL_SOLVER_AVAILABLE:
        if heuristic == "lexicographic" and not pure_literal:
            return DPLLSolver()  # type: ignore[misc]
        cfg = DPLLConfig(heuristic=heuristic, enable_pure_literal=pure_literal)  # type: ignore[misc]
        return DPLLSolver(config=cfg)  # type: ignore[misc]
    warnings.warn(
        "Real TV3 solver not found in `solver/`; falling back to temporary StubDPLLSolver "
        f"(heuristic={heuristic!r}, pure_literal={pure_literal} ignored). "
        "Do NOT use stub figures in final report.",
        UserWarning,
        stacklevel=2,
    )
    return StubDPLLSolver()
