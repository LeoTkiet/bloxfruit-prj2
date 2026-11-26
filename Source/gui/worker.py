"""Background worker thread for non-blocking Auto Solve with step-by-step animation."""

from __future__ import annotations

import inspect
import time
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.contracts.interfaces import IGameEngine, ILogicAgent
from core.contracts.models import (
    CellID,
    Clue,
    DeductionStep,
    PublicState,
    Status,
    VerdictResponse,
)


def _supports_on_step(agent: ILogicAgent) -> bool:
    """Detect whether `agent.run_auto_solve` accepts an optional `on_step` callback."""
    try:
        sig = inspect.signature(agent.run_auto_solve)
    except (TypeError, ValueError):
        return False
    return "on_step" in sig.parameters or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )


class _StepTrackingEngineProxy:
    """Transparent `IGameEngine` proxy capturing each intermediate `PublicState`.

    Used when an `ILogicAgent` implementation does not expose an `on_step`
    callback so the GUI can still animate every single deduction step cleanly
    at the chosen playback speed.
    """

    def __init__(self, inner: IGameEngine) -> None:
        self._inner = inner
        self.verdict_snapshots: list[PublicState] = []

    def load_puzzle(self, path: str | Path) -> PublicState:
        return self._inner.load_puzzle(path)

    def get_public_state(self) -> PublicState:
        return self._inner.get_public_state()

    def submit_verdict(self, cell: CellID, status: Status) -> VerdictResponse:
        resp = self._inner.submit_verdict(cell, status)
        self.verdict_snapshots.append(resp.public_state)
        return resp

    def restart(self) -> PublicState:
        return self._inner.restart()

    def get_highlighted_cells(self, cell: CellID) -> list[CellID]:
        return self._inner.get_highlighted_cells(cell)

    def get_all_clues_for_uniqueness(self) -> list[Clue]:
        return self._inner.get_all_clues_for_uniqueness()


class AutoSolveWorker(QThread):
    """Runs `agent.run_auto_solve(engine)` off the UI thread.

    Emits `step_produced(DeductionStep, PublicState)` after each deduction step so
    the GUI updates smoothly without freezing, supporting Normal, Slow, and Instant
    playback speeds for both callback-aware agents (TV4) and standard `ILogicAgent`
    implementations.
    """

    step_produced = pyqtSignal(object, object)
    finished_solve = pyqtSignal(list, object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        agent: ILogicAgent,
        engine: IGameEngine,
        *,
        delay_ms: int = 450,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._agent = agent
        self._engine = engine
        self._delay_ms = max(0, delay_ms)
        self._skip_delay = False

    def skip_remaining_delays(self) -> None:
        """Finish remaining steps immediately without artificial UI delay."""
        self._skip_delay = True

    def _sleep_interruptible(self) -> None:
        if self._delay_ms <= 0 or self._skip_delay:
            return
        remaining = self._delay_ms
        while remaining > 0 and not self._skip_delay and not self.isInterruptionRequested():
            chunk = min(25, remaining)
            time.sleep(chunk / 1000.0)
            remaining -= chunk

    def run(self) -> None:
        try:
            if _supports_on_step(self._agent):
                def _on_step(step: DeductionStep) -> None:
                    snapshot: PublicState = self._engine.get_public_state()
                    self.step_produced.emit(step, snapshot)
                    self._sleep_interruptible()

                run_fn: Any = self._agent.run_auto_solve
                steps: list[DeductionStep] = run_fn(self._engine, on_step=_on_step)
            else:
                initial_snap = self._engine.get_public_state()
                proxy = _StepTrackingEngineProxy(self._engine)
                steps = self._agent.run_auto_solve(proxy)

                snap_idx = 0
                last_snap = initial_snap
                for step in steps:
                    if step.cell is not None and snap_idx < len(proxy.verdict_snapshots):
                        last_snap = proxy.verdict_snapshots[snap_idx]
                        snap_idx += 1
                    self.step_produced.emit(step, last_snap)
                    self._sleep_interruptible()

            final_state = self._engine.get_public_state()
            self.finished_solve.emit(steps, final_state)
        except Exception as exc:  # pragma: no cover - defensive guard for UI stability
            self.failed.emit(str(exc))
