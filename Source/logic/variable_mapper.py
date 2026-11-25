"""Deterministic cell <-> propositional variable mapping (owned by TV2).

Primary variables follow a fixed row-major order:

    A1 -> 1, B1 -> 2, ..., C3 -> 9  (for a 3x3 grid)

Auxiliary variables introduced by CNF encodings are allocated strictly after
``grid_size ** 2`` so they can never collide with a primary variable.
"""

from __future__ import annotations

from core.contracts.models import CellID, all_cell_ids, coords_to_cell_id, parse_cell_id

__all__ = [
    "AuxVarAllocator",
    "VariableMapper",
    "cell_to_var",
    "var_to_cell",
]


def _validate_grid_size(grid_size: int) -> None:
    if not isinstance(grid_size, int) or isinstance(grid_size, bool):
        raise ValueError(f"grid_size must be an integer, got {grid_size!r}")
    if not (1 <= grid_size <= 26):
        raise ValueError(f"grid_size must be in [1, 26], got {grid_size}")


def cell_to_var(cell: CellID, grid_size: int) -> int:
    """Map a canonical CellID to its 1-based primary variable index.

    The mapping is deterministic row-major: ``(row, col) -> row * N + col + 1``.
    """
    _validate_grid_size(grid_size)
    if not isinstance(cell, str):
        raise ValueError(f"CellID must be a string, got {cell!r}")
    row_idx, col_idx = parse_cell_id(cell)
    if not (0 <= row_idx < grid_size and 0 <= col_idx < grid_size):
        raise ValueError(
            f"Cell {cell!r} is out of bounds for a {grid_size}x{grid_size} grid"
        )
    return row_idx * grid_size + col_idx + 1


def var_to_cell(var_id: int, grid_size: int) -> CellID:
    """Map a 1-based primary variable index back to its canonical CellID."""
    _validate_grid_size(grid_size)
    if not isinstance(var_id, int) or isinstance(var_id, bool):
        raise ValueError(f"var_id must be an integer, got {var_id!r}")
    num_primary = grid_size * grid_size
    if not (1 <= var_id <= num_primary):
        raise ValueError(f"Primary var_id {var_id!r} out of range [1, {num_primary}]")
    row_idx, col_idx = divmod(var_id - 1, grid_size)
    return coords_to_cell_id(row_idx, col_idx)


class VariableMapper:
    """Reusable, immutable mapping for one fixed grid size.

    Instances are convenient when many cells are mapped repeatedly; the
    module-level helpers above are used by `CNFEncoder` for stateless calls.
    """

    def __init__(self, grid_size: int) -> None:
        _validate_grid_size(grid_size)
        self._grid_size = grid_size
        cells = all_cell_ids(grid_size)
        self._cell_to_var: dict[CellID, int] = {
            cell: idx + 1 for idx, cell in enumerate(cells)
        }
        self._var_to_cell: dict[int, CellID] = {
            idx + 1: cell for idx, cell in enumerate(cells)
        }

    @property
    def grid_size(self) -> int:
        return self._grid_size

    @property
    def num_primary_vars(self) -> int:
        return self._grid_size * self._grid_size

    def map_cell_to_var(self, cell: CellID) -> int:
        if not isinstance(cell, str):
            raise ValueError(f"CellID must be a string, got {cell!r}")
        key = cell.upper()
        if key not in self._cell_to_var:
            raise ValueError(
                f"Cell {cell!r} is not part of a {self._grid_size}x{self._grid_size} grid"
            )
        return self._cell_to_var[key]

    def map_var_to_cell(self, var_id: int) -> CellID:
        if var_id not in self._var_to_cell:
            raise ValueError(
                f"Primary var_id {var_id!r} out of range "
                f"[1, {self.num_primary_vars}]"
            )
        return self._var_to_cell[var_id]

    def all_variables(self) -> tuple[int, ...]:
        """Return all primary variable indices in deterministic order."""
        return tuple(range(1, self.num_primary_vars + 1))


class AuxVarAllocator:
    """Sequential allocator for auxiliary variables of a single KB encoding.

    Allocation starts at ``num_primary_vars + 1`` and is monotonic within one
    encoder run, guaranteeing globally unique auxiliary literals in KB_t.
    """

    def __init__(self, num_primary_vars: int) -> None:
        if not isinstance(num_primary_vars, int) or isinstance(num_primary_vars, bool):
            raise ValueError(
                f"num_primary_vars must be an integer, got {num_primary_vars!r}"
            )
        if num_primary_vars < 1:
            raise ValueError(f"num_primary_vars must be >= 1, got {num_primary_vars}")
        self._num_primary_vars = num_primary_vars
        self._next_var = num_primary_vars + 1

    def alloc(self) -> int:
        """Allocate and return the next unused auxiliary variable index."""
        var = self._next_var
        self._next_var += 1
        return var

    @property
    def num_aux_vars(self) -> int:
        """Number of auxiliary variables allocated so far."""
        return self._next_var - self._num_primary_vars - 1

    @property
    def next_var(self) -> int:
        """Index that the next `alloc()` call will return."""
        return self._next_var
