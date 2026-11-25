"""Tests for TV2's deterministic variable mapping and auxiliary allocator."""

from __future__ import annotations

import pytest

from logic.variable_mapper import AuxVarAllocator, VariableMapper, cell_to_var, var_to_cell


def test_row_major_mapping_is_deterministic() -> None:
    expected = {
        "A1": 1,
        "B1": 2,
        "C1": 3,
        "A2": 4,
        "B2": 5,
        "C2": 6,
        "A3": 7,
        "B3": 8,
        "C3": 9,
    }
    for cell, var in expected.items():
        assert cell_to_var(cell, 3) == var
        assert var_to_cell(var, 3) == cell


def test_mapping_larger_grid() -> None:
    assert cell_to_var("E5", 5) == 25
    assert var_to_cell(21, 5) == "A5"
    assert cell_to_var("A1", 2) == 1


@pytest.mark.parametrize("cell", ["D1", "A4", "Z1", ""])
def test_out_of_bounds_or_malformed_cells_are_rejected(cell: str) -> None:
    with pytest.raises(ValueError):
        cell_to_var(cell, 3)


def test_primary_variable_bounds_are_rejected() -> None:
    for var in (0, 10, -1):
        with pytest.raises(ValueError):
            var_to_cell(var, 3)


def test_variable_mapper_instance_api() -> None:
    mapper = VariableMapper(3)
    assert mapper.grid_size == 3
    assert mapper.num_primary_vars == 9
    assert mapper.all_variables() == tuple(range(1, 10))
    assert mapper.map_cell_to_var("c2") == 6
    assert mapper.map_var_to_cell(6) == "C2"
    with pytest.raises(ValueError):
        mapper.map_cell_to_var("D1")
    with pytest.raises(ValueError):
        mapper.map_var_to_cell(10)


def test_auxiliary_allocator_starts_after_primary_variables() -> None:
    allocator = AuxVarAllocator(9)
    assert allocator.num_aux_vars == 0
    assert allocator.next_var == 10
    assert [allocator.alloc() for _ in range(3)] == [10, 11, 12]
    assert allocator.num_aux_vars == 3
    assert allocator.next_var == 13


def test_auxiliary_allocator_rejects_invalid_primary_count() -> None:
    for count in (0, -1):
        with pytest.raises(ValueError):
            AuxVarAllocator(count)
