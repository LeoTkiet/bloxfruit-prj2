"""Tests for TV2's automatic CNF encoder and statistics."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.contracts.interfaces import ICNFEncoder
from core.contracts.models import (
    Clue,
    ClueType,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
)
from engine.game_engine import GameEngine
from logic.cnf_encoder import CNFEncoder


def _clue(**kwargs) -> Clue:
    defaults = dict(clue_id="test", owner="A1", clue_type=ClueType.FACT, text="")
    defaults.update(kwargs)
    return Clue(**defaults)


def test_contract_compliance_and_strategy() -> None:
    encoder = CNFEncoder()
    assert isinstance(encoder, ICNFEncoder)
    assert encoder.cardinality_encoding == "direct"
    assert CNFEncoder("sinz").cardinality_encoding == "sinz"
    with pytest.raises(ValueError):
        CNFEncoder("unknown")


def test_mapper_and_resolver_methods() -> None:
    encoder = CNFEncoder()
    assert encoder.map_cell_to_var("C2", 3) == 6
    assert encoder.map_var_to_cell(6, 3) == "C2"
    assert encoder.resolve_region(RegionSpec(RegionType.ROW, row=2), 3) == [
        "A2",
        "B2",
        "C2",
    ]


def test_binary_clue_encodings_are_exact() -> None:
    encoder = CNFEncoder()
    fact = _clue(target="B2", target_status=Status.CRIMINAL)
    assert encoder.encode_clue(fact, 3) == [[5]]
    fact_innocent = _clue(target="B2", target_status=Status.INNOCENT)
    assert encoder.encode_clue(fact_innocent, 3) == [[-5]]

    same = _clue(
        clue_id="same",
        clue_type=ClueType.SAME,
        targets=("A1", "C2"),
    )
    assert encoder.encode_clue(same, 3) == [[-1, 6], [1, -6]]

    different = _clue(
        clue_id="different",
        clue_type=ClueType.DIFFERENT,
        targets=("A1", "C2"),
    )
    assert encoder.encode_clue(different, 3) == [[1, 6], [-1, -6]]


def test_direct_cardinality_clause_counts() -> None:
    encoder = CNFEncoder()
    region = RegionSpec(RegionType.EXPLICIT, cells=("A1", "B1", "C1"))

    at_most = _clue(
        clue_id="at_most",
        clue_type=ClueType.AT_MOST,
        region=region,
        count=1,
    )
    assert len(encoder.encode_clue(at_most, 3)) == 3  # C(3, 2)

    at_least = _clue(
        clue_id="at_least",
        clue_type=ClueType.AT_LEAST,
        region=region,
        count=2,
    )
    assert len(encoder.encode_clue(at_least, 3)) == 3  # C(3, 2)

    exactly = _clue(
        clue_id="exactly",
        clue_type=ClueType.EXACTLY,
        region=region,
        count=1,
    )
    # C(3, 3) = 1 clause for AT_LEAST(1) + C(3, 2) = 3 for AT_MOST(1)
    assert len(encoder.encode_clue(exactly, 3)) == 4

    no_clue = _clue(
        clue_id="no",
        clue_type=ClueType.EXACTLY,
        region=region,
        count=0,
    )
    assert encoder.encode_clue(no_clue, 3) == [[-1], [-2], [-3]]


def test_sinz_strategy_allocates_shared_auxiliary_variables() -> None:
    encoder = CNFEncoder("sinz")
    region = RegionSpec(RegionType.EXPLICIT, cells=("A1", "B1", "C1", "A2"))
    clue = _clue(
        clue_id="sinz",
        clue_type=ClueType.AT_MOST,
        region=region,
        count=1,
    )
    formula, stats = encoder.encode_clues([clue, clue], grid_size=3)
    assert stats.encoding_strategy == "sinz"
    assert stats.num_primary_vars == 9
    assert stats.num_aux_vars == 6  # (4 - 1) * 1 per clue, shared allocator
    assert formula.num_vars == 15
    assert max(abs(lit) for clause in formula.clauses for lit in clause) <= 15


def test_encode_kb_uses_only_public_knowledge() -> None:
    puzzle_path = Path(__file__).resolve().parents[2] / "puzzles" / "3x3" / "3x3_01_precinct_basics.json"
    engine = GameEngine()
    state = engine.load_puzzle(puzzle_path)

    encoder = CNFEncoder()
    formula, stats = encoder.encode_kb(state)

    assert stats.num_primary_vars == 9
    assert stats.num_clauses == len(formula.clauses)
    assert stats.num_aux_vars == formula.num_aux_vars
    assert formula.num_vars == stats.num_primary_vars + stats.num_aux_vars
    assert len(formula.var_to_cell) == 9
    assert len(formula.cell_to_var) == 9

    # Proved verdicts appear as unit clauses in row-major order.
    units = [cell for cell, status in state.proved_verdicts.items() if status != Status.UNKNOWN]
    expected_unit_literals = {encoder.map_cell_to_var(cell, 3) for cell in units}
    actual_unit_literals = {
        clause[0] for clause in formula.clauses if len(clause) == 1
    }
    assert expected_unit_literals.issubset({abs(lit) for lit in actual_unit_literals})


def test_encoding_is_deterministic() -> None:
    clue = _clue(
        clue_id="parity",
        clue_type=ClueType.PARITY,
        region=RegionSpec(RegionType.ROW, row=2),
        parity=ParityKind.EVEN,
    )
    first = CNFEncoder().encode_clue(clue, 3)
    second = CNFEncoder().encode_clue(clue, 3)
    assert first == second


@pytest.mark.parametrize(
    "clue",
    [
        _clue(clue_id="bad_fact", target="A1", target_status=Status.UNKNOWN),
        _clue(clue_id="bad_same", clue_type=ClueType.SAME, targets=("A1", "A1")),
        _clue(
            clue_id="bad_count",
            clue_type=ClueType.EXACTLY,
            region=RegionSpec(RegionType.EXPLICIT, cells=("A1", "B1")),
            count=3,
        ),
        _clue(
            clue_id="bad_parity",
            clue_type=ClueType.PARITY,
            region=RegionSpec(RegionType.ROW, row=1),
            parity=None,
        ),
    ],
)
def test_invalid_clues_are_rejected(clue: Clue) -> None:
    with pytest.raises(ValueError):
        CNFEncoder().encode_clue(clue, 3)
