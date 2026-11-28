"""Semantic verification tests for `experiments.stub_encoder.StubCNFEncoder`."""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from core.contracts.interfaces import ICNFEncoder
from core.contracts.models import (
    Clue,
    ClueType,
    CNFFormula,
    CompareOp,
    RegionSpec,
    RegionType,
    Status,
    all_cell_ids,
)
from engine.puzzle_loader import load_puzzle_definition
from experiments.stub_encoder import StubCNFEncoder
from experiments.solver_factory import make_solver
from tests.test_agent.conftest import PUZZLES_DIR, make_public_state
from tests.test_engine.mock_agent import evaluate_clue_truth

THREE_BY_THREE_PUZZLES = sorted(
    list((PUZZLES_DIR / "3x3").glob("*.json"))
    + list((PUZZLES_DIR / "edge_cases").glob("*.json"))
    + [p for p in (PUZZLES_DIR / "extensions").glob("*3x3*.json")]
)


def test_stub_encoder_conforms_to_protocol_and_row_major_mapping() -> None:
    encoder = StubCNFEncoder()
    assert isinstance(encoder, ICNFEncoder)

    assert encoder.map_cell_to_var("A1", 3) == 1
    assert encoder.map_cell_to_var("B1", 3) == 2
    assert encoder.map_cell_to_var("C1", 3) == 3
    assert encoder.map_cell_to_var("A2", 3) == 4
    assert encoder.map_cell_to_var("C3", 3) == 9
    assert encoder.map_cell_to_var("E5", 5) == 25

    with pytest.raises(ValueError):
        encoder.map_cell_to_var("D1", 3)


@pytest.mark.parametrize(
    "puzzle_path",
    THREE_BY_THREE_PUZZLES,
    ids=[p.relative_to(PUZZLES_DIR).as_posix() for p in THREE_BY_THREE_PUZZLES],
)
def test_stub_encoder_matches_oracle_on_all_512_assignments_for_3x3_puzzles(
    puzzle_path: Path,
) -> None:
    """Verify CNF solution set == evaluate_clue_truth over all 2^9 = 512 assignments."""
    puzzle = load_puzzle_definition(puzzle_path)
    assert puzzle.grid_size == 3

    encoder = StubCNFEncoder()
    solver = make_solver()
    cells = all_cell_ids(3)

    all_assignments = list(product((False, True), repeat=9))

    for ch in puzzle.characters:
        clue = ch.hidden_clue
        raw_clauses = encoder.encode_clue(clue, 3)
        cnf = CNFFormula(
            clauses=tuple(tuple(c) for c in raw_clauses),
            num_primary_vars=9,
            num_aux_vars=max(
                0,
                max((abs(lit) for cl in raw_clauses for lit in cl), default=9) - 9,
            ),
        )
        for bits in all_assignments:
            assignment = {cells[i]: bits[i] for i in range(9)}
            expected = evaluate_clue_truth(clue, assignment, 3)
            assumptions = [i + 1 if bits[i] else -(i + 1) for i in range(9)]
            sat_res = solver.solve(cnf, assumptions=assumptions)
            assert sat_res.is_sat == expected, (
                f"{puzzle.puzzle_id} {clue.clue_id}: CNF sat={sat_res.is_sat} "
                f"!= oracle={expected} on {assignment}"
            )


def test_stub_encoder_compare_counts_and_sinz_large_region_semantics() -> None:
    """Verify COMPARE_COUNTS (all 5 ops) and Sinz cardinality (m > 8) match oracle."""
    encoder = StubCNFEncoder()
    solver = make_solver()
    cells_3x3 = all_cell_ids(3)
    all_assignments = list(product((False, True), repeat=9))

    # Overlapping regions for COMPARE_COUNTS on 3x3
    reg_a = RegionSpec(region_type=RegionType.EXPLICIT, cells=("A1", "B1", "A2"))
    reg_b = RegionSpec(region_type=RegionType.EXPLICIT, cells=("B1", "C1", "B2", "C2"))

    for op in CompareOp:
        clue = Clue(
            clue_id=f"cmp_{op.value}",
            owner="A1",
            clue_type=ClueType.COMPARE_COUNTS,
            region=reg_a,
            region_b=reg_b,
            compare_op=op,
        )
        raw_clauses = encoder.encode_clue(clue, 3)
        max_var = max((abs(lit) for cl in raw_clauses for lit in cl), default=9)
        cnf = CNFFormula(
            clauses=tuple(tuple(c) for c in raw_clauses),
            num_primary_vars=9,
            num_aux_vars=max(0, max_var - 9),
        )
        for bits in all_assignments:
            assignment = {cells_3x3[i]: bits[i] for i in range(9)}
            expected = evaluate_clue_truth(clue, assignment, 3)
            assumptions = [i + 1 if bits[i] else -(i + 1) for i in range(9)]
            assert solver.solve(cnf, assumptions=assumptions).is_sat == expected

    # Sinz cardinality path (m = 12 > 8) on 4x4 BOUNDARY
    boundary_cells = encoder.resolve_region(
        RegionSpec(region_type=RegionType.BOUNDARY), 4
    )
    assert len(boundary_cells) == 12
    cells_4x4 = all_cell_ids(4)

    for ctype, k in (
        (ClueType.EXACTLY, 5),
        (ClueType.AT_LEAST, 4),
        (ClueType.AT_MOST, 3),
    ):
        clue = Clue(
            clue_id=f"sinz_{ctype.value}_{k}",
            owner="A1",
            clue_type=ctype,
            region=RegionSpec(region_type=RegionType.BOUNDARY),
            count=k,
        )
        state = make_public_state(4, revealed_clues=(clue,))
        cnf, stats = encoder.encode_kb(state)
        assert stats.encoding_strategy == "stub"
        assert stats.num_primary_vars == 16
        assert stats.num_aux_vars > 0

        # Sample edge counts (0, 1, 11, 12), prefix subsets, and non-prefix subsets
        sampled_subsets = [boundary_cells[:num_crim] for num_crim in range(len(boundary_cells) + 1)]
        sampled_subsets.extend(
            [
                boundary_cells[1::2],        # alternating 6 cells
                boundary_cells[::2],         # alternating 6 cells
                boundary_cells[-5:],         # suffix 5 cells
                boundary_cells[:2] + boundary_cells[-2:],  # 4 corner-ish cells
                boundary_cells[3:6],         # middle 3 cells
            ]
        )
        for subset in sampled_subsets:
            assignment = {cid: False for cid in cells_4x4}
            for cid in subset:
                assignment[cid] = True
            expected = evaluate_clue_truth(clue, assignment, 4)
            assumptions = [
                encoder.map_cell_to_var(cid, 4)
                if assignment[cid]
                else -encoder.map_cell_to_var(cid, 4)
                for cid in cells_4x4
            ]
            assert solver.solve(cnf, assumptions=assumptions).is_sat == expected


def test_stub_encoder_encode_kb_uses_revealed_clues_and_proved_verdicts() -> None:
    encoder = StubCNFEncoder()
    clue_a1 = Clue(
        clue_id="c_a1",
        owner="A1",
        clue_type=ClueType.SAME,
        targets=("A1", "B1"),
    )
    state = make_public_state(
        2,
        proved_verdicts={"A1": Status.CRIMINAL},
        revealed_clues=(clue_a1,),
    )
    cnf, stats = encoder.encode_kb(state)
    assert stats.num_primary_vars == 4
    assert stats.encoding_strategy == "stub"
    assert (1,) in cnf.clauses  # Unit clause for proved A1=CRIMINAL
    assert stats.num_clauses == len(cnf.clauses)
    res = make_solver().solve(cnf)
    assert res.is_sat and res.model is not None
    assert res.model[1] is True
    assert res.model[2] is True
