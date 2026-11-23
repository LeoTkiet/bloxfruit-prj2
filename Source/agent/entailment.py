"""SAT-based logical entailment and model-caching classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from core.contracts.interfaces import ISATSolver
from core.contracts.models import (
    CellID,
    CNFFormula,
    SATMetrics,
    SATQueryLog,
    Status,
    parse_cell_id,
)


def sort_cells_row_major(cells: Sequence[CellID]) -> list[CellID]:
    """Sort CellIDs deterministically in row-major order (A1, B1, ..., A2, ...)."""
    return sorted(cells, key=parse_cell_id)


@dataclass(frozen=True)
class EntailmentResult:
    """Complete consistency and per-cell entailment result for a KB_t."""

    consistent: bool
    classification: dict[CellID, Status]
    sat_queries: tuple[SATQueryLog, ...]
    models: tuple[Mapping[int, bool], ...]
    real_sat_calls: int


def check_kb_consistency(
    cnf: CNFFormula,
    solver: ISATSolver,
) -> tuple[bool, Optional[Mapping[int, bool]], SATQueryLog]:
    """Check whether `cnf` is satisfiable and return (is_sat, model, query_log)."""
    res = solver.solve(cnf)
    query = SATQueryLog(
        cell="KB",
        assumptions=(),
        is_sat=res.is_sat,
        metrics=res.metrics,
        cached=False,
    )
    return res.is_sat, (res.model if res.is_sat else None), query


def classify_single_cell(
    cnf: CNFFormula,
    cell: CellID,
    var_id: int,
    solver: ISATSolver,
    *,
    use_model_cache: bool = True,
    known_models: Sequence[Mapping[int, bool]] = (),
) -> tuple[Status, tuple[SATQueryLog, ...], list[Mapping[int, bool]], int]:
    """Classify one unsolved cell via refutation assuming `cnf` is already SAT."""
    queries: list[SATQueryLog] = []
    new_models: list[Mapping[int, bool]] = []
    real_calls = 0

    can_be_innocent = use_model_cache and any(
        m.get(var_id) is False for m in known_models
    )
    can_be_criminal = use_model_cache and any(
        m.get(var_id) is True for m in known_models
    )

    if can_be_innocent:
        queries.append(
            SATQueryLog(
                cell=cell,
                assumptions=(-var_id,),
                is_sat=True,
                metrics=SATMetrics(),
                cached=True,
            )
        )
    else:
        res_neg = solver.solve(cnf, (-var_id,))
        real_calls += 1
        queries.append(
            SATQueryLog(
                cell=cell,
                assumptions=(-var_id,),
                is_sat=res_neg.is_sat,
                metrics=res_neg.metrics,
                cached=False,
            )
        )
        if not res_neg.is_sat:
            return Status.CRIMINAL, tuple(queries), new_models, real_calls
        if res_neg.model is not None:
            new_models.append(res_neg.model)

    if can_be_criminal:
        queries.append(
            SATQueryLog(
                cell=cell,
                assumptions=(var_id,),
                is_sat=True,
                metrics=SATMetrics(),
                cached=True,
            )
        )
    else:
        res_pos = solver.solve(cnf, (var_id,))
        real_calls += 1
        queries.append(
            SATQueryLog(
                cell=cell,
                assumptions=(var_id,),
                is_sat=res_pos.is_sat,
                metrics=res_pos.metrics,
                cached=False,
            )
        )
        if not res_pos.is_sat:
            return Status.INNOCENT, tuple(queries), new_models, real_calls
        if res_pos.model is not None:
            new_models.append(res_pos.model)

    return Status.UNKNOWN, tuple(queries), new_models, real_calls


def classify_board(
    cnf: CNFFormula,
    unsolved_cells: Sequence[CellID],
    cell_to_var: Mapping[CellID, int],
    solver: ISATSolver,
    *,
    use_model_cache: bool = True,
    prechecked_consistency: Optional[
        tuple[bool, Optional[Mapping[int, bool]], Optional[SATQueryLog]]
    ] = None,
    seed_models: Sequence[Mapping[int, bool]] = (),
) -> EntailmentResult:
    """Check consistency of `cnf` and classify all `unsolved_cells` via refutation."""
    queries: list[SATQueryLog] = []
    models: list[Mapping[int, bool]] = []
    real_calls = 0

    if prechecked_consistency is not None:
        is_sat, base_model, base_query = prechecked_consistency
        if base_query is not None:
            queries.append(base_query)
    else:
        is_sat, base_model, base_query = check_kb_consistency(cnf, solver)
        real_calls += 1
        queries.append(base_query)

    if not is_sat:
        return EntailmentResult(
            consistent=False,
            classification={},
            sat_queries=tuple(queries),
            models=(),
            real_sat_calls=real_calls,
        )

    ordered_cells = sort_cells_row_major(unsolved_cells)
    can_be_criminal: dict[CellID, bool] = {cid: False for cid in ordered_cells}
    can_be_innocent: dict[CellID, bool] = {cid: False for cid in ordered_cells}

    def record_model(model: Optional[Mapping[int, bool]]) -> None:
        if model is None:
            return
        models.append(model)
        if not use_model_cache:
            return
        for cid in ordered_cells:
            v = cell_to_var[cid]
            if v in model:
                if model[v]:
                    can_be_criminal[cid] = True
                else:
                    can_be_innocent[cid] = True

    record_model(base_model)
    for m in seed_models:
        record_model(m)

    classification: dict[CellID, Status] = {}

    for cid in ordered_cells:
        v = cell_to_var[cid]

        # Test KB & ~v (refutes INNOCENT -> entails CRIMINAL)
        if use_model_cache and can_be_innocent[cid]:
            queries.append(
                SATQueryLog(
                    cell=cid,
                    assumptions=(-v,),
                    is_sat=True,
                    metrics=SATMetrics(),
                    cached=True,
                )
            )
        else:
            res_neg = solver.solve(cnf, (-v,))
            real_calls += 1
            queries.append(
                SATQueryLog(
                    cell=cid,
                    assumptions=(-v,),
                    is_sat=res_neg.is_sat,
                    metrics=res_neg.metrics,
                    cached=False,
                )
            )
            if not res_neg.is_sat:
                classification[cid] = Status.CRIMINAL
                continue
            record_model(res_neg.model)

        # Test KB & +v (refutes CRIMINAL -> entails INNOCENT)
        if use_model_cache and can_be_criminal[cid]:
            queries.append(
                SATQueryLog(
                    cell=cid,
                    assumptions=(v,),
                    is_sat=True,
                    metrics=SATMetrics(),
                    cached=True,
                )
            )
        else:
            res_pos = solver.solve(cnf, (v,))
            real_calls += 1
            queries.append(
                SATQueryLog(
                    cell=cid,
                    assumptions=(v,),
                    is_sat=res_pos.is_sat,
                    metrics=res_pos.metrics,
                    cached=False,
                )
            )
            if not res_pos.is_sat:
                classification[cid] = Status.INNOCENT
                continue
            record_model(res_pos.model)

        classification[cid] = Status.UNKNOWN

    return EntailmentResult(
        consistent=True,
        classification=classification,
        sat_queries=tuple(queries),
        models=tuple(models),
        real_sat_calls=real_calls,
    )
