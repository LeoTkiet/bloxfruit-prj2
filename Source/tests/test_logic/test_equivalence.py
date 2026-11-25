"""100% equivalence test: direct semantics vs. generated CNF.

For every clue template (core + extensions) and both cardinality strategies,
the CNF formula must be satisfiable under a primary-variable assignment exactly
when the direct semantic evaluator says the clue holds — with no help from
TV3's SAT solver.
"""

from __future__ import annotations

import itertools
import random
from pathlib import Path
from typing import Iterable

from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CompareOp,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
    all_cell_ids,
)
from engine.puzzle_loader import load_puzzle_definition
from logic.cnf_encoder import CNFEncoder
from logic.evaluator import DirectSemanticEvaluator
from tests.test_logic.equivalence_helpers import sat_exists_under

STRATEGIES = ("direct", "sinz")


def _clue(**kwargs) -> Clue:
    defaults = dict(clue_id="equivalence", owner="A1", clue_type=ClueType.FACT, text="")
    defaults.update(kwargs)
    return Clue(**defaults)


def _crafted_clues() -> list[Clue]:
    """Hand-built clues guaranteeing coverage of every supported template."""
    explicit3 = RegionSpec(RegionType.EXPLICIT, cells=("A1", "B1", "C1", "A2"))
    row2 = RegionSpec(RegionType.ROW, row=2)
    col_a = RegionSpec(RegionType.COL, col="A")
    return [
        _clue(clue_id="fact_c", target="A1", target_status=Status.CRIMINAL),
        _clue(clue_id="fact_i", target="A1", target_status=Status.INNOCENT),
        _clue(clue_id="same", clue_type=ClueType.SAME, targets=("A1", "C2")),
        _clue(clue_id="different", clue_type=ClueType.DIFFERENT, targets=("A1", "C2")),
        *[
            _clue(
                clue_id=f"{ct.value}_{k}",
                clue_type=ct,
                region=explicit3,
                count=k,
            )
            for ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST)
            for k in range(5)
        ],
        *[
            _clue(
                clue_id=f"parity_{kind.value}",
                clue_type=ClueType.PARITY,
                region=row2,
                parity=kind,
            )
            for kind in (ParityKind.EVEN, ParityKind.ODD)
        ],
        *[
            _clue(
                clue_id=f"compare_{op.value}",
                clue_type=ClueType.COMPARE_COUNTS,
                region=col_a,
                region_b=row2,
                compare_op=op,
            )
            for op in CompareOp
        ],
        _clue(
            clue_id="intersection",
            clue_type=ClueType.EXACTLY,
            region=RegionSpec(
                RegionType.INTERSECTION,
                sub_regions=(
                    RegionSpec(RegionType.NEIGHBORS, center="B2"),
                    RegionSpec(RegionType.COL, col="B"),
                ),
            ),
            count=1,
        ),
        _clue(
            clue_id="common_neighbors",
            clue_type=ClueType.PARITY,
            region=RegionSpec(RegionType.COMMON_NEIGHBORS, cells=("A1", "C1")),
            parity=ParityKind.EVEN,
        ),
        _clue(
            clue_id="corners",
            clue_type=ClueType.AT_MOST,
            region=RegionSpec(RegionType.CORNERS),
            count=2,
        ),
        _clue(
            clue_id="boundary",
            clue_type=ClueType.AT_LEAST,
            region=RegionSpec(RegionType.BOUNDARY),
            count=3,
        ),
        _clue(
            clue_id="between",
            clue_type=ClueType.EXACTLY,
            region=RegionSpec(RegionType.BETWEEN, cells=("A1", "A3")),
            count=0,
        ),
    ]


def _puzzle_clues(sizes: set[int]) -> list[tuple[Clue, int]]:
    puzzle_dir = Path(__file__).resolve().parents[2] / "puzzles"
    result: list[tuple[Clue, int]] = []
    for path in sorted(puzzle_dir.rglob("*.json")):
        puzzle = load_puzzle_definition(path)
        if puzzle.grid_size not in sizes:
            continue
        result.extend(
            (character.hidden_clue, puzzle.grid_size)
            for character in puzzle.characters
        )
    return result


def _assignments_3x3() -> Iterable[dict[CellID, bool]]:
    cells = all_cell_ids(3)
    for bits in itertools.product((False, True), repeat=9):
        yield dict(zip(cells, bits))


def _sampled_assignments(grid_size: int, count: int) -> Iterable[dict[CellID, bool]]:
    cells = all_cell_ids(grid_size)
    rng = random.Random(20261125)
    for _ in range(count):
        bits = [rng.choice((False, True)) for _ in cells]
        yield dict(zip(cells, bits))


def _assert_equivalence(
    clues: list[tuple[Clue, int]],
    assignments_provider,
    strategies: Iterable[str] = STRATEGIES,
) -> None:
    evaluator = DirectSemanticEvaluator()
    checks = 0
    for strategy in strategies:
        encoder = CNFEncoder(strategy)
        for clue, grid_size in clues:
            clauses = encoder.encode_clue(clue, grid_size)
            for assignment in assignments_provider(grid_size):
                expected = evaluator.evaluate_clue_direct(clue, assignment, grid_size)
                primary = {
                    var_id: assignment[cell]
                    for cell, var_id in encoder_map(encoder, grid_size).items()
                }
                actual = sat_exists_under(clauses, primary)
                assert actual is expected, (
                    f"clue={clue.clue_id} strategy={strategy} "
                    f"assignment={assignment}"
                )
                checks += 1
    assert checks > 0


def encoder_map(encoder: CNFEncoder, grid_size: int) -> dict[CellID, int]:
    cells = all_cell_ids(grid_size)
    return {cell: encoder.map_cell_to_var(cell, grid_size) for cell in cells}


def test_all_crafted_clues_are_equivalent_on_all_3x3_assignments() -> None:
    """6 core + extension templates x 512 assignments x 2 strategies."""
    _assert_equivalence(
        [(clue, 3) for clue in _crafted_clues()],
        lambda size: _assignments_3x3(),
    )


def test_all_3x3_puzzle_clues_are_equivalent() -> None:
    _assert_equivalence(
        _puzzle_clues({3}),
        lambda size: _assignments_3x3(),
    )


def test_larger_puzzle_clues_are_equivalent_on_sampled_assignments() -> None:
    _assert_equivalence(
        _puzzle_clues({4, 5}),
        lambda size: _sampled_assignments(size, 12),
    )


def test_sinz_is_equivalent_on_region_larger_than_direct_threshold() -> None:
    """Force the sequential-counter path (9 cells > direct threshold of 8)."""
    region = RegionSpec(
        RegionType.EXPLICIT,
        cells=("A1", "B1", "C1", "D1", "A2", "B2", "C2", "D2", "A3"),
    )
    clues = [
        _clue(
            clue_id=f"sinz_{ctype.value}_{k}",
            clue_type=ctype,
            region=region,
            count=k,
        )
        for ctype in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST)
        for k in (1, 3, 5, 8)
    ]
    cells = all_cell_ids(4)
    other_cells = [cell for cell in cells if cell not in region.cells]

    def assignments(size: int) -> Iterable[dict[CellID, bool]]:
        assert size == 4
        for bits in itertools.product((False, True), repeat=len(region.cells)):
            partial = dict(zip(region.cells, bits))
            yield {**{cell: False for cell in other_cells}, **partial}

    _assert_equivalence([(clue, 4) for clue in clues], assignments, strategies=("sinz",))
