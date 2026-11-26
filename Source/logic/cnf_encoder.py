"""Automatic, reusable CNF encoder for Griductive knowledge bases (owned by TV2).

Implements `ICNFEncoder`. Every active clue is compiled to CNF automatically —
there is **no** hand-written CNF for any individual puzzle. Two interchangeable
cardinality strategies are provided:

* ``direct``: combinatorial clauses over primary literals only (no aux vars);
* ``sinz``: Sinz sequential counter using O(|R| * k) auxiliary variables.

PARITY uses a Tseitin XOR chain and COMPARE_COUNTS uses exact unary counters.
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Mapping, Optional, Sequence

from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CNFFormula,
    CNFStats,
    CompareOp,
    ParityKind,
    PublicState,
    RegionSpec,
    Status,
    all_cell_ids,
)
from logic.region_resolver import resolve_region_cells
from logic.variable_mapper import AuxVarAllocator, cell_to_var, var_to_cell

__all__ = ["CNFEncoder"]

CARDINALITY_STRATEGIES = ("direct", "sinz")

# Regions are at most 8 neighbors / 5 row or column cells in the core game, so
# direct combinatorial encoding stays compact without auxiliary variables.
_DIRECT_CARDINALITY_THRESHOLD = 8


class CNFEncoder:
    """Reusable encoder implementing `ICNFEncoder` from the shared contracts."""

    def __init__(self, cardinality_encoding: str = "direct") -> None:
        if cardinality_encoding not in CARDINALITY_STRATEGIES:
            raise ValueError(
                f"cardinality_encoding must be one of {CARDINALITY_STRATEGIES}, "
                f"got {cardinality_encoding!r}"
            )
        self._cardinality_encoding = cardinality_encoding

    @property
    def cardinality_encoding(self) -> str:
        return self._cardinality_encoding

    # ------------------------------------------------------------------
    # ICNFEncoder implementation
    # ------------------------------------------------------------------

    def map_cell_to_var(self, cell: CellID, grid_size: int) -> int:
        """Deterministically map a CellID to its primary variable (1..N^2)."""
        return cell_to_var(cell, grid_size)

    def map_var_to_cell(self, var_id: int, grid_size: int) -> CellID:
        """Inverse mapping for primary variables (useful for SAT models)."""
        return var_to_cell(var_id, grid_size)

    def resolve_region(self, region: RegionSpec, grid_size: int) -> list[CellID]:
        """Resolve a RegionSpec into deterministic row-major distinct CellIDs."""
        return resolve_region_cells(region, grid_size)

    def encode_clue(self, clue: Clue, grid_size: int) -> list[list[int]]:
        """Encode one clue into CNF clauses with a fresh local allocator."""
        allocator = AuxVarAllocator(grid_size * grid_size)
        return self._encode_clue_with_allocator(clue, grid_size, allocator)

    def encode_kb(self, public_state: PublicState) -> tuple[CNFFormula, CNFStats]:
        """Encode KB_t from revealed clues and proved verdicts only."""
        return self.encode_clues(
            clues=public_state.revealed_clues,
            grid_size=public_state.grid_size,
            known_verdicts=public_state.proved_verdicts,
        )

    def encode_clues(
        self,
        clues: Sequence[Clue] | Iterable[Clue],
        grid_size: int,
        known_verdicts: Optional[Mapping[CellID, Status]] = None,
    ) -> tuple[CNFFormula, CNFStats]:
        """Encode a set of clues (plus optional verdict units) into one formula.

        A single `AuxVarAllocator` is shared across all clues so auxiliary
        variables are globally unique in the resulting KB_t.
        """
        if not isinstance(grid_size, int) or isinstance(grid_size, bool):
            raise ValueError(f"grid_size must be an integer, got {grid_size!r}")
        if grid_size < 1 or grid_size > 26:
            raise ValueError(f"grid_size must be in [1, 26], got {grid_size}")

        num_primary = grid_size * grid_size
        allocator = AuxVarAllocator(num_primary)
        clauses: list[tuple[int, ...]] = []

        for clue in clues:
            for clause in self._encode_clue_with_allocator(clue, grid_size, allocator):
                clauses.append(tuple(clause))

        # Known verdicts become unit clauses, in deterministic row-major order.
        if known_verdicts is not None:
            for cell in all_cell_ids(grid_size):
                status = known_verdicts.get(cell)
                if status in (Status.CRIMINAL, Status.INNOCENT):
                    literal = cell_to_var(cell, grid_size)
                    clauses.append((literal if status == Status.CRIMINAL else -literal,))
                elif status not in (None, Status.UNKNOWN):
                    raise ValueError(
                        f"Invalid proved status {status!r} for cell {cell!r}"
                    )

        cells = all_cell_ids(grid_size)
        var_to_cell = {cell_to_var(cell, grid_size): cell for cell in cells}
        cell_to_var_map = {cell: var for var, cell in var_to_cell.items()}

        formula = CNFFormula(
            clauses=tuple(clauses),
            num_primary_vars=num_primary,
            num_aux_vars=allocator.num_aux_vars,
            var_to_cell=var_to_cell,
            cell_to_var=cell_to_var_map,
        )
        stats = CNFStats(
            num_primary_vars=num_primary,
            num_aux_vars=allocator.num_aux_vars,
            num_clauses=len(clauses),
            encoding_strategy=self._cardinality_encoding,
        )
        return formula, stats

    # ------------------------------------------------------------------
    # Clue dispatch
    # ------------------------------------------------------------------

    def _encode_clue_with_allocator(
        self,
        clue: Clue,
        grid_size: int,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        clue_type = clue.clue_type
        context = repr(clue.clue_id)

        if clue_type == ClueType.FACT:
            if clue.target is None or clue.target_status not in (
                Status.CRIMINAL,
                Status.INNOCENT,
            ):
                raise ValueError(f"Invalid FACT clue {context}")
            var = cell_to_var(clue.target, grid_size)
            literal = var if clue.target_status == Status.CRIMINAL else -var
            return [[literal]]

        if clue_type in (ClueType.SAME, ClueType.DIFFERENT):
            if len(clue.targets) != 2:
                raise ValueError(f"{clue_type.value} clue {context} requires 2 targets")
            first, second = clue.targets
            v1 = cell_to_var(first, grid_size)
            v2 = cell_to_var(second, grid_size)
            if v1 == v2:
                raise ValueError(f"{clue_type.value} clue {context} requires distinct targets")
            if clue_type == ClueType.SAME:
                # C_i <-> C_j  ==  (~C_i or C_j) and (C_i or ~C_j)
                return [[-v1, v2], [v1, -v2]]
            # C_i xor C_j  ==  (C_i or C_j) and (~C_i or ~C_j)
            return [[v1, v2], [-v1, -v2]]

        if clue_type in (
            ClueType.EXACTLY,
            ClueType.AT_LEAST,
            ClueType.AT_MOST,
        ):
            if clue.region is None:
                raise ValueError(f"Cardinality clue {context} requires a region")
            count = clue.count
            if not isinstance(count, int) or isinstance(count, bool):
                raise ValueError(f"Cardinality clue {context} requires an integer count")
            literals = [
                cell_to_var(cell, grid_size)
                for cell in resolve_region_cells(clue.region, grid_size)
            ]
            size = len(literals)
            if not (0 <= count <= size):
                raise ValueError(
                    f"Count {count} out of range [0, {size}] for clue {context}"
                )
            if clue_type == ClueType.AT_MOST:
                return self._encode_at_most(literals, count, allocator)
            if clue_type == ClueType.AT_LEAST:
                return self._encode_at_least(literals, count, allocator)
            return self._encode_at_least(
                literals, count, allocator
            ) + self._encode_at_most(literals, count, allocator)

        if clue_type == ClueType.PARITY:
            if clue.region is None or clue.parity not in (
                ParityKind.EVEN,
                ParityKind.ODD,
            ):
                raise ValueError(f"Invalid PARITY clue {context}")
            literals = [
                cell_to_var(cell, grid_size)
                for cell in resolve_region_cells(clue.region, grid_size)
            ]
            return self._encode_parity(
                literals, clue.parity == ParityKind.ODD, allocator
            )

        if clue_type == ClueType.COMPARE_COUNTS:
            if (
                clue.region is None
                or clue.region_b is None
                or clue.compare_op not in tuple(CompareOp)
            ):
                raise ValueError(f"Invalid COMPARE_COUNTS clue {context}")
            left = [
                cell_to_var(cell, grid_size)
                for cell in resolve_region_cells(clue.region, grid_size)
            ]
            right = [
                cell_to_var(cell, grid_size)
                for cell in resolve_region_cells(clue.region_b, grid_size)
            ]
            return self._encode_compare_counts(
                left, right, clue.compare_op, allocator
            )

        raise ValueError(f"Unsupported clue type: {clue_type!r}")

    # ------------------------------------------------------------------
    # Cardinality encodings
    # ------------------------------------------------------------------

    def _encode_at_most(
        self,
        literals: list[int],
        k: int,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode ``sum(literals) <= k``."""
        size = len(literals)
        if k >= size:
            return []
        if k == 0:
            return [[-literal] for literal in literals]
        if self._cardinality_encoding == "direct" and size <= _DIRECT_CARDINALITY_THRESHOLD:
            # Every (k+1)-subset would contain at least one false literal.
            return [[-lit for lit in subset] for subset in combinations(literals, k + 1)]
        return self._encode_at_most_sinz(literals, k, allocator)

    def _encode_at_least(
        self,
        literals: list[int],
        k: int,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode ``sum(literals) >= k`` via ``sum(~literal) <= size - k``."""
        size = len(literals)
        if k <= 0:
            return []
        if k == size:
            return [[literal] for literal in literals]
        if self._cardinality_encoding == "direct" and size <= _DIRECT_CARDINALITY_THRESHOLD:
            # Every (size-k+1)-subset must contain at least one true literal.
            return [list(subset) for subset in combinations(literals, size - k + 1)]
        return self._encode_at_most_sinz([-lit for lit in literals], size - k, allocator)

    @staticmethod
    def _encode_at_most_sinz(
        literals: list[int],
        k: int,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        """Sinz sequential counter for ``sum(literals) <= k`` (1 <= k < size).

        ``s[i][j]`` means "among literals[0..i], at least j+1 are true".
        """
        size = len(literals)
        if not (1 <= k < size):
            raise ValueError(f"Sinz encoding requires 1 <= k < size, got k={k}, size={size}")

        states = [[allocator.alloc() for _ in range(k)] for _ in range(size - 1)]
        clauses: list[list[int]] = [[-literals[0], states[0][0]]]
        for j in range(1, k):
            clauses.append([-states[0][j]])

        for i in range(1, size - 1):
            clauses.append([-literals[i], states[i][0]])
            clauses.append([-states[i - 1][0], states[i][0]])
            for j in range(1, k):
                clauses.append([-literals[i], -states[i - 1][j - 1], states[i][j]])
                clauses.append([-states[i - 1][j], states[i][j]])
            clauses.append([-literals[i], -states[i - 1][k - 1]])

        clauses.append([-literals[size - 1], -states[size - 2][k - 1]])
        return clauses

    @staticmethod
    def _encode_parity(
        literals: list[int],
        want_odd: bool,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode XOR of all literals via a Tseitin chain."""
        size = len(literals)
        if size == 0:
            return [[]] if want_odd else []
        if size == 1:
            return [[literals[0] if want_odd else -literals[0]]]

        clauses: list[list[int]] = []
        accumulator = literals[0]
        for literal in literals[1:-1]:
            output = allocator.alloc()
            # output <-> (accumulator XOR literal)
            clauses.extend(
                [
                    [-accumulator, -literal, -output],
                    [accumulator, literal, -output],
                    [-accumulator, literal, output],
                    [accumulator, -literal, output],
                ]
            )
            accumulator = output

        last = literals[-1]
        if want_odd:
            clauses.extend([[accumulator, last], [-accumulator, -last]])
        else:
            clauses.extend([[-accumulator, last], [accumulator, -last]])
        return clauses

    @staticmethod
    def _build_unary_counter(
        literals: list[int],
        allocator: AuxVarAllocator,
    ) -> tuple[list[int], list[list[int]]]:
        """Build exact thermometer outputs ``out[j-1] <-> (sum >= j)``."""
        size = len(literals)
        if size == 0:
            return [], []
        if size == 1:
            return [literals[0]], []

        clauses: list[list[int]] = []
        previous = [literals[0]]
        for literal in literals[1:]:
            current: list[int] = []
            first = allocator.alloc()
            clauses.extend(
                [
                    [-previous[0], first],
                    [-literal, first],
                    [-first, previous[0], literal],
                ]
            )
            current.append(first)

            for j in range(2, len(previous) + 1):
                output = allocator.alloc()
                same = previous[j - 1]
                before = previous[j - 2]
                clauses.extend(
                    [
                        [-same, output],
                        [-before, -literal, output],
                        [-output, same, before],
                        [-output, same, literal],
                    ]
                )
                current.append(output)

            top = allocator.alloc()
            clauses.extend(
                [
                    [-previous[-1], -literal, top],
                    [-top, previous[-1]],
                    [-top, literal],
                ]
            )
            current.append(top)
            previous = current

        return previous, clauses

    def _encode_compare_counts(
        self,
        left: list[int],
        right: list[int],
        op: CompareOp,
        allocator: AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode ``count(left) <op> count(right)`` using exact unary counters."""
        left_ge, left_clauses = self._build_unary_counter(left, allocator)
        right_ge, right_clauses = self._build_unary_counter(right, allocator)
        clauses = left_clauses + right_clauses

        if op == CompareOp.EQ:
            clauses.extend(self._encode_unary_le(left_ge, right_ge))
            clauses.extend(self._encode_unary_le(right_ge, left_ge))
        elif op == CompareOp.LE:
            clauses.extend(self._encode_unary_le(left_ge, right_ge))
        elif op == CompareOp.GE:
            clauses.extend(self._encode_unary_le(right_ge, left_ge))
        elif op == CompareOp.LT:
            clauses.extend(self._encode_unary_lt(left_ge, right_ge))
        elif op == CompareOp.GT:
            clauses.extend(self._encode_unary_lt(right_ge, left_ge))
        else:
            raise ValueError(f"Unsupported CompareOp: {op!r}")
        return clauses

    @staticmethod
    def _encode_unary_le(a_ge: list[int], b_ge: list[int]) -> list[list[int]]:
        """Encode ``count(A) <= count(B)`` from thermometer vectors."""
        clauses: list[list[int]] = []
        for idx in range(min(len(a_ge), len(b_ge))):
            clauses.append([-a_ge[idx], b_ge[idx]])
        if len(a_ge) > len(b_ge):
            clauses.append([-a_ge[len(b_ge)]])
        return clauses

    @staticmethod
    def _encode_unary_lt(a_ge: list[int], b_ge: list[int]) -> list[list[int]]:
        """Encode ``count(A) < count(B)`` from thermometer vectors."""
        if not b_ge:
            return [[]]
        clauses: list[list[int]] = [[b_ge[0]]]
        for idx in range(min(len(a_ge), len(b_ge) - 1)):
            clauses.append([-a_ge[idx], b_ge[idx + 1]])
        if len(a_ge) >= len(b_ge):
            clauses.append([-a_ge[len(b_ge) - 1]])
        return clauses
