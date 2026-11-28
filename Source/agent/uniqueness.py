"""Independent puzzle uniqueness verification via primary-variable blocking."""

from __future__ import annotations

from typing import Sequence

from core.contracts.interfaces import ICNFEncoder, ISATSolver
from core.contracts.models import (
    CellID,
    CharacterPublicInfo,
    Clue,
    CNFFormula,
    PublicState,
    Status,
    UniquenessResult,
    all_cell_ids,
)


def check_uniqueness(
    clues: Sequence[Clue],
    grid_size: int,
    encoder: ICNFEncoder,
    solver: ISATSolver,
) -> UniquenessResult:
    """Verify whether `clues` admits 0 (UNSAT), 1 (UNIQUE), or >=2 (MULTIPLE) solutions.

    Encodes all clues together via a synthetic unrevealed `PublicState` and builds
    the blocking clause strictly over primary variables `1..N^2`.
    """
    cells = all_cell_ids(grid_size)
    characters = tuple(
        CharacterPublicInfo(
            cell_id=cid,
            name=cid,
            profession="Unknown",
            status=Status.UNKNOWN,
            is_revealed=False,
            clue=None,
        )
        for cid in cells
    )
    synthetic_state = PublicState(
        puzzle_id="__uniqueness__",
        puzzle_name="Uniqueness Check",
        grid_size=grid_size,
        step=0,
        characters=characters,
        proved_verdicts={},
        revealed_clues=tuple(clues),
        is_solved=False,
    )

    cnf, _stats = encoder.encode_kb(synthetic_state)
    res_first = solver.solve(cnf)

    if not res_first.is_sat or res_first.model is None:
        return UniquenessResult(
            is_unique=False,
            solution_count_status="UNSAT",
            first_model=None,
            second_model=None,
            metrics_first=res_first.metrics,
            metrics_second=None,
        )

    cell_vars: list[tuple[CellID, int]] = [
        (cid, encoder.map_cell_to_var(cid, grid_size)) for cid in cells
    ]
    first_model = {
        cid: (
            Status.CRIMINAL
            if res_first.model.get(var, False)
            else Status.INNOCENT
        )
        for cid, var in cell_vars
    }

    # Block ONLY on primary variables 1..N^2 so auxiliary variables never cause false multiples
    blocking_clause = tuple(
        -var if res_first.model.get(var, False) else var for _, var in cell_vars
    )
    blocked_cnf = CNFFormula(
        clauses=cnf.clauses + (blocking_clause,),
        num_primary_vars=cnf.num_primary_vars,
        num_aux_vars=cnf.num_aux_vars,
        var_to_cell=cnf.var_to_cell,
        cell_to_var=cnf.cell_to_var,
    )

    res_second = solver.solve(blocked_cnf)
    if not res_second.is_sat or res_second.model is None:
        return UniquenessResult(
            is_unique=True,
            solution_count_status="UNIQUE",
            first_model=first_model,
            second_model=None,
            metrics_first=res_first.metrics,
            metrics_second=res_second.metrics,
        )

    second_model = {
        cid: (
            Status.CRIMINAL
            if res_second.model.get(var, False)
            else Status.INNOCENT
        )
        for cid, var in cell_vars
    }
    return UniquenessResult(
        is_unique=False,
        solution_count_status="MULTIPLE",
        first_model=first_model,
        second_model=second_model,
        metrics_first=res_first.metrics,
        metrics_second=res_second.metrics,
    )
