"""Deductive Logic Agent implementing `ILogicAgent` without guessing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from agent.entailment import (
    check_kb_consistency,
    classify_board,
    classify_single_cell,
    sort_cells_row_major,
)
from agent.hint_engine import build_hint
from agent.kb_cache import KBCache, KBCacheEntry, make_kb_key
from agent.outcome import AutoSolveOutcome, outcome_of
from agent.uniqueness import check_uniqueness as _check_uniqueness
from core.contracts.interfaces import ICNFEncoder, IGameEngine, ISATSolver
from core.contracts.models import (
    CellID,
    Clue,
    CNFStats,
    DeductionStep,
    HintResult,
    PublicState,
    SATQueryLog,
    Status,
    UniquenessResult,
    VerdictCode,
    all_cell_ids,
)

logger = logging.getLogger("agent")


@dataclass
class AgentStats:
    """Separated SAT call counters for deduction vs engine validation."""

    deduction_sat_calls: int = 0
    validation_sat_calls: int = 0


class DeductiveLogicAgent:
    """No-guess deductive logic agent backed by injected `ICNFEncoder` and `ISATSolver`."""

    def __init__(
        self,
        encoder: ICNFEncoder,
        solver: ISATSolver,
        *,
        use_model_cache: bool = True,
        kb_cache_size: int = 8,
    ) -> None:
        self._encoder: ICNFEncoder = encoder
        self._solver: ISATSolver = solver
        self._use_model_cache: bool = use_model_cache
        self._kb_cache: KBCache = KBCache(maxsize=kb_cache_size)
        self.stats: AgentStats = AgentStats()
        self.last_outcome: Optional[AutoSolveOutcome] = None
        self._in_validation: bool = False

    @property
    def use_model_cache(self) -> bool:
        return self._use_model_cache

    def reset_stats(self) -> None:
        """Reset SAT call counters."""
        self.stats.deduction_sat_calls = 0
        self.stats.validation_sat_calls = 0

    def clear_cache(self) -> None:
        """Clear the KB-level LRU cache."""
        self._kb_cache.clear()

    def _record_sat_calls(self, count: int) -> None:
        if count <= 0:
            return
        if self._in_validation:
            self.stats.validation_sat_calls += count
        else:
            self.stats.deduction_sat_calls += count

    def _cell_to_var_map(self, grid_size: int) -> dict[CellID, int]:
        return {
            cid: self._encoder.map_cell_to_var(cid, grid_size)
            for cid in all_cell_ids(grid_size)
        }

    def _ensure_consistency_entry(self, state: PublicState) -> KBCacheEntry:
        key = make_kb_key(state)
        entry = self._kb_cache.get(key)
        if entry is not None:
            return entry

        cnf, cnf_stats = self._encoder.encode_kb(state)
        is_sat, model, query = check_kb_consistency(cnf, self._solver)
        self._record_sat_calls(1)

        entry = KBCacheEntry(
            consistent=is_sat,
            cnf=cnf,
            cnf_stats=cnf_stats,
            classification={},
            fully_classified=not is_sat,
            sat_queries=(query,),
            models=[model] if model is not None else [],
            initial_query=query,
        )
        self._kb_cache.put(key, entry)
        return entry

    def _classify_all_with_trace(
        self,
        state: PublicState,
    ) -> tuple[bool, dict[CellID, Status], tuple[SATQueryLog, ...], CNFStats]:
        key = make_kb_key(state)
        entry = self._kb_cache.get(key)
        if entry is not None and entry.fully_classified:
            return (
                entry.consistent,
                dict(entry.classification),
                entry.sat_queries,
                entry.cnf_stats,
            )

        if entry is not None:
            cnf = entry.cnf
            cnf_stats = entry.cnf_stats
            prechecked = (
                entry.consistent,
                entry.models[0] if entry.models else None,
                entry.initial_query,
            )
            seed_models = entry.models[1:]
        else:
            cnf, cnf_stats = self._encoder.encode_kb(state)
            prechecked = None
            seed_models = ()

        cell_to_var = self._cell_to_var_map(state.grid_size)
        res = classify_board(
            cnf=cnf,
            unsolved_cells=state.unsolved_cells,
            cell_to_var=cell_to_var,
            solver=self._solver,
            use_model_cache=self._use_model_cache,
            prechecked_consistency=prechecked,
            seed_models=seed_models,
        )
        self._record_sat_calls(res.real_sat_calls)

        initial_query = (
            entry.initial_query
            if entry is not None
            else (res.sat_queries[0] if res.sat_queries else None)
        )
        new_entry = KBCacheEntry(
            consistent=res.consistent,
            cnf=cnf,
            cnf_stats=cnf_stats,
            classification=dict(res.classification),
            fully_classified=True,
            sat_queries=res.sat_queries,
            models=list(res.models),
            initial_query=initial_query,
        )
        self._kb_cache.put(key, new_entry)
        return (
            res.consistent,
            dict(res.classification),
            res.sat_queries,
            cnf_stats,
        )

    # ------------------------------------------------------------------
    # ILogicAgent implementation
    # ------------------------------------------------------------------

    def check_consistency(self, state: PublicState) -> bool:
        """Return True iff KB_t derived from `state` is satisfiable."""
        return self._ensure_consistency_entry(state).consistent

    def classify_character(self, state: PublicState, cell: CellID) -> Status:
        """Classify `cell` via logical entailment: CRIMINAL, INNOCENT, or UNKNOWN."""
        cell_upper = cell.upper()
        state.get_character(cell_upper)  # Validates cell belongs to board

        entry = self._ensure_consistency_entry(state)
        if not entry.consistent:
            return Status.UNKNOWN

        if cell_upper in state.proved_verdicts:
            return state.proved_verdicts[cell_upper]

        if cell_upper in entry.classification:
            return entry.classification[cell_upper]

        var_id = self._encoder.map_cell_to_var(cell_upper, state.grid_size)
        status, _queries, new_models, real_calls = classify_single_cell(
            cnf=entry.cnf,
            cell=cell_upper,
            var_id=var_id,
            solver=self._solver,
            use_model_cache=self._use_model_cache,
            known_models=entry.models,
        )
        self._record_sat_calls(real_calls)
        entry.models.extend(new_models)
        entry.classification[cell_upper] = status
        return status

    def classify_all(self, state: PublicState) -> dict[CellID, Status]:
        """Classify every unsolved character in `state` via logical entailment."""
        consistent, classification, _, _ = self._classify_all_with_trace(state)
        if not consistent:
            return {}
        return classification

    def get_hint(self, state: PublicState) -> HintResult:
        """Identify one currently forced character and relevant revealed clues."""

        def _classify_for_hint(s: PublicState) -> tuple[bool, dict[CellID, Status]]:
            consistent, classification, _, _ = self._classify_all_with_trace(s)
            return consistent, classification

        return build_hint(state, self._encoder, _classify_for_hint)

    def run_auto_solve(
        self,
        engine: IGameEngine,
        on_step: Optional[Callable[[DeductionStep], None]] = None,
    ) -> list[DeductionStep]:
        """Run the no-guess deduction loop until SOLVED, AMBIGUOUS, or INCONSISTENT."""
        steps: list[DeductionStep] = []

        def _notify(step: DeductionStep) -> None:
            if on_step is not None:
                try:
                    on_step(step)
                except Exception as exc:
                    logger.warning("on_step callback raised an exception: %s", exc)

        while True:
            state = engine.get_public_state()
            if state.is_solved or not state.unsolved_cells:
                break

            active_clue_ids = tuple(c.clue_id for c in state.revealed_clues)
            consistent, classification, sat_queries, cnf_stats = (
                self._classify_all_with_trace(state)
            )

            if not consistent:
                terminal_step = DeductionStep(
                    step_number=state.step + 1,
                    active_clue_ids=active_clue_ids,
                    sat_queries=sat_queries,
                    cell=None,
                    verdict=Status.UNKNOWN,
                    verdict_code=VerdictCode.INCONSISTENT,
                    revealed_clue=None,
                    cnf_stats=cnf_stats,
                )
                steps.append(terminal_step)
                _notify(terminal_step)
                break

            unsolved_sorted = sort_cells_row_major(state.unsolved_cells)
            chosen: Optional[tuple[CellID, Status]] = None
            for cid in unsolved_sorted:
                st = classification.get(cid, Status.UNKNOWN)
                if st in (Status.CRIMINAL, Status.INNOCENT):
                    chosen = (cid, st)
                    break

            if chosen is None:
                logger.warning(
                    "AMBIGUOUS state reached: puzzle_id=%s, step=%d, unknown_cells=%s",
                    state.puzzle_id,
                    state.step,
                    list(unsolved_sorted),
                )
                terminal_step = DeductionStep(
                    step_number=state.step + 1,
                    active_clue_ids=active_clue_ids,
                    sat_queries=sat_queries,
                    cell=None,
                    verdict=Status.UNKNOWN,
                    verdict_code=VerdictCode.NOT_PROVABLE,
                    revealed_clue=None,
                    cnf_stats=cnf_stats,
                )
                steps.append(terminal_step)
                _notify(terminal_step)
                break

            chosen_cell, chosen_verdict = chosen
            self._in_validation = True
            try:
                resp = engine.submit_verdict(chosen_cell, chosen_verdict)
            finally:
                self._in_validation = False

            step_num = (
                resp.public_state.step
                if resp.code == VerdictCode.ACCEPTED
                else state.step + 1
            )
            step = DeductionStep(
                step_number=step_num,
                active_clue_ids=active_clue_ids,
                sat_queries=sat_queries,
                cell=chosen_cell,
                verdict=chosen_verdict,
                verdict_code=resp.code,
                revealed_clue=resp.revealed_clue,
                cnf_stats=cnf_stats,
            )
            steps.append(step)
            _notify(step)

            if resp.code != VerdictCode.ACCEPTED:
                break

        self.last_outcome = outcome_of(steps, engine.get_public_state())
        return steps

    def check_uniqueness(
        self,
        clues: Sequence[Clue],
        grid_size: int,
    ) -> UniquenessResult:
        """Verify whether the complete clue set has a unique satisfying assignment."""
        return _check_uniqueness(clues, grid_size, self._encoder, self._solver)
