"""Temporary StubCNFEncoder implementing `ICNFEncoder` for TV4 Phase 1.

Maps grid cells deterministically in row-major order (`A1`=1, `B1`=2, ...) and
encodes all core and extension clue types (`FACT`, `SAME`, `DIFFERENT`, `EXACTLY`,
`AT_LEAST`, `AT_MOST`, `PARITY`, `COMPARE_COUNTS`) into CNF.
Will be replaced by TV2's `logic.CNFEncoder` during integration.
"""

from __future__ import annotations

from itertools import combinations
from typing import Mapping, Optional, Sequence

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
    coords_to_cell_id,
    parse_cell_id,
)
from engine.puzzle_validator import resolve_region_cells

_DIRECT_CARDINALITY_THRESHOLD = 8


class _AuxVarAllocator:
    """Sequential auxiliary variable allocator starting after primary vars."""

    def __init__(self, num_primary_vars: int) -> None:
        self._num_primary = num_primary_vars
        self._next_var = num_primary_vars + 1

    def alloc(self) -> int:
        var = self._next_var
        self._next_var += 1
        return var

    @property
    def num_aux_vars(self) -> int:
        return self._next_var - (self._num_primary + 1)


class StubCNFEncoder:
    """Temporary `ICNFEncoder` implementation for TV4 development and testing."""

    def __init__(self, *, inject_free_aux_vars: int = 0) -> None:
        if inject_free_aux_vars < 0:
            raise ValueError(
                f"inject_free_aux_vars must be >= 0, got {inject_free_aux_vars}"
            )
        self._inject_free_aux_vars = inject_free_aux_vars

    def map_cell_to_var(self, cell: CellID, grid_size: int) -> int:
        """Map canonical CellID (`A1`..`EN`) to row-major 1-based variable index."""
        row_idx, col_idx = parse_cell_id(cell)
        if not (0 <= row_idx < grid_size and 0 <= col_idx < grid_size):
            raise ValueError(
                f"Cell {cell!r} out of bounds for {grid_size}x{grid_size} grid"
            )
        return row_idx * grid_size + col_idx + 1

    def map_var_to_cell(self, var_id: int, grid_size: int) -> CellID:
        """Map 1-based primary variable index back to row-major CellID."""
        num_primary = grid_size * grid_size
        if not (1 <= var_id <= num_primary):
            raise ValueError(
                f"Primary var_id {var_id} out of range [1, {num_primary}]"
            )
        zero_idx = var_id - 1
        row_idx, col_idx = divmod(zero_idx, grid_size)
        return coords_to_cell_id(row_idx, col_idx)

    def resolve_region(self, region: RegionSpec, grid_size: int) -> list[CellID]:
        """Resolve a RegionSpec into deterministic row-major distinct CellIDs."""
        return resolve_region_cells(region, grid_size)

    def encode_clue(self, clue: Clue, grid_size: int) -> list[list[int]]:
        """Encode a single structured Clue into CNF clauses."""
        alloc = _AuxVarAllocator(grid_size * grid_size)
        return self._encode_clue_with_allocator(clue, grid_size, alloc)

    def encode_kb(self, public_state: PublicState) -> tuple[CNFFormula, CNFStats]:
        """Encode KB_t from `public_state.revealed_clues` and `proved_verdicts`."""
        return self.encode_clues(
            clues=public_state.revealed_clues,
            grid_size=public_state.grid_size,
            known_verdicts=public_state.proved_verdicts,
        )

    def encode_clues(
        self,
        clues: Sequence[Clue],
        grid_size: int,
        known_verdicts: Optional[Mapping[CellID, Status]] = None,
    ) -> tuple[CNFFormula, CNFStats]:
        """Encode a sequence of clues and optional known verdicts into a CNFFormula."""
        num_primary = grid_size * grid_size
        alloc = _AuxVarAllocator(num_primary)
        clauses: list[tuple[int, ...]] = []

        for clue in clues:
            for clause in self._encode_clue_with_allocator(clue, grid_size, alloc):
                clauses.append(tuple(clause))

        if known_verdicts:
            for cid in all_cell_ids(grid_size):
                status = known_verdicts.get(cid)
                if status == Status.CRIMINAL:
                    clauses.append((self.map_cell_to_var(cid, grid_size),))
                elif status == Status.INNOCENT:
                    clauses.append((-self.map_cell_to_var(cid, grid_size),))

        for _ in range(self._inject_free_aux_vars):
            alloc.alloc()

        cells = all_cell_ids(grid_size)
        var_to_cell = {self.map_cell_to_var(cid, grid_size): cid for cid in cells}
        cell_to_var = {cid: v for v, cid in var_to_cell.items()}

        formula = CNFFormula(
            clauses=tuple(clauses),
            num_primary_vars=num_primary,
            num_aux_vars=alloc.num_aux_vars,
            var_to_cell=var_to_cell,
            cell_to_var=cell_to_var,
        )
        stats = CNFStats(
            num_primary_vars=num_primary,
            num_aux_vars=alloc.num_aux_vars,
            num_clauses=len(clauses),
            encoding_strategy="stub",
        )
        return formula, stats

    # ------------------------------------------------------------------
    # Clue encodings
    # ------------------------------------------------------------------

    def _encode_clue_with_allocator(
        self,
        clue: Clue,
        grid_size: int,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        ct = clue.clue_type

        if ct == ClueType.FACT:
            if clue.target is None or clue.target_status not in (
                Status.CRIMINAL,
                Status.INNOCENT,
            ):
                raise ValueError(f"Invalid FACT clue {clue.clue_id!r}")
            v = self.map_cell_to_var(clue.target, grid_size)
            return [[v if clue.target_status == Status.CRIMINAL else -v]]

        if ct == ClueType.SAME:
            if len(clue.targets) != 2:
                raise ValueError(f"SAME clue {clue.clue_id!r} requires 2 targets")
            v1 = self.map_cell_to_var(clue.targets[0], grid_size)
            v2 = self.map_cell_to_var(clue.targets[1], grid_size)
            return [[-v1, v2], [v1, -v2]]

        if ct == ClueType.DIFFERENT:
            if len(clue.targets) != 2:
                raise ValueError(f"DIFFERENT clue {clue.clue_id!r} requires 2 targets")
            v1 = self.map_cell_to_var(clue.targets[0], grid_size)
            v2 = self.map_cell_to_var(clue.targets[1], grid_size)
            return [[v1, v2], [-v1, -v2]]

        if ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
            if clue.region is None or clue.count is None:
                raise ValueError(f"Cardinality clue {clue.clue_id!r} missing region/count")
            cells = self.resolve_region(clue.region, grid_size)
            vars_list = [self.map_cell_to_var(c, grid_size) for c in cells]
            k = clue.count
            if not (0 <= k <= len(vars_list)):
                raise ValueError(
                    f"Count {k} out of range [0, {len(vars_list)}] for {clue.clue_id!r}"
                )
            if ct == ClueType.AT_MOST:
                return self._encode_at_most(vars_list, k, alloc)
            if ct == ClueType.AT_LEAST:
                return self._encode_at_least(vars_list, k, alloc)
            return self._encode_at_least(vars_list, k, alloc) + self._encode_at_most(
                vars_list, k, alloc
            )

        if ct == ClueType.PARITY:
            if clue.region is None or clue.parity not in (
                ParityKind.EVEN,
                ParityKind.ODD,
            ):
                raise ValueError(f"Invalid PARITY clue {clue.clue_id!r}")
            cells = self.resolve_region(clue.region, grid_size)
            vars_list = [self.map_cell_to_var(c, grid_size) for c in cells]
            return self._encode_parity(vars_list, clue.parity == ParityKind.ODD, alloc)

        if ct == ClueType.COMPARE_COUNTS:
            if (
                clue.region is None
                or clue.region_b is None
                or clue.compare_op is None
            ):
                raise ValueError(f"Invalid COMPARE_COUNTS clue {clue.clue_id!r}")
            cells_a = self.resolve_region(clue.region, grid_size)
            cells_b = self.resolve_region(clue.region_b, grid_size)
            vars_a = [self.map_cell_to_var(c, grid_size) for c in cells_a]
            vars_b = [self.map_cell_to_var(c, grid_size) for c in cells_b]
            return self._encode_compare_counts(vars_a, vars_b, clue.compare_op, alloc)

        raise ValueError(f"Unsupported clue type: {ct!r}")

    def _encode_at_most(
        self,
        lits: list[int],
        k: int,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode sum(lits are True) <= k."""
        m = len(lits)
        if k >= m:
            return []
        if k == 0:
            return [[-lit] for lit in lits]
        if m <= _DIRECT_CARDINALITY_THRESHOLD:
            return [[-lit for lit in comb] for comb in combinations(lits, k + 1)]
        return self._encode_at_most_sinz(lits, k, alloc)

    def _encode_at_least(
        self,
        lits: list[int],
        k: int,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode sum(lits are True) >= k via sum(not lit) <= m - k."""
        m = len(lits)
        if k <= 0:
            return []
        if k == m:
            return [[lit] for lit in lits]
        if m <= _DIRECT_CARDINALITY_THRESHOLD:
            return [list(comb) for comb in combinations(lits, m - k + 1)]
        return self._encode_at_most_sinz([-lit for lit in lits], m - k, alloc)

    def _encode_at_most_sinz(
        self,
        lits: list[int],
        k: int,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        """Sinz sequential counter for sum(lits) <= k with 1 <= k < len(lits)."""
        m = len(lits)
        # s[i][j] holds True if sum(lits[0..i]) >= j + 1 (i in 0..m-2, j in 0..k-1)
        s = [[alloc.alloc() for _ in range(k)] for _ in range(m - 1)]
        clauses: list[list[int]] = []

        clauses.append([-lits[0], s[0][0]])
        for j in range(1, k):
            clauses.append([-s[0][j]])

        for i in range(1, m - 1):
            clauses.append([-lits[i], s[i][0]])
            clauses.append([-s[i - 1][0], s[i][0]])
            for j in range(1, k):
                clauses.append([-lits[i], -s[i - 1][j - 1], s[i][j]])
                clauses.append([-s[i - 1][j], s[i][j]])
            clauses.append([-lits[i], -s[i - 1][k - 1]])

        clauses.append([-lits[m - 1], -s[m - 2][k - 1]])
        return clauses

    def _encode_parity(
        self,
        vars_list: list[int],
        want_odd: bool,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode XOR parity constraint using Tseitin auxiliary variables."""
        m = len(vars_list)
        if m == 0:
            return [[]] if want_odd else []
        if m == 1:
            return [[vars_list[0] if want_odd else -vars_list[0]]]

        clauses: list[list[int]] = []
        acc = vars_list[0]
        for idx in range(1, m - 1):
            nxt = vars_list[idx]
            out = alloc.alloc()
            # out <-> (acc XOR nxt)
            clauses.append([-acc, -nxt, -out])
            clauses.append([acc, nxt, -out])
            clauses.append([-acc, nxt, out])
            clauses.append([acc, -nxt, out])
            acc = out

        last = vars_list[-1]
        if want_odd:
            # acc XOR last == True
            clauses.append([acc, last])
            clauses.append([-acc, -last])
        else:
            # acc XOR last == False
            clauses.append([-acc, last])
            clauses.append([acc, -last])
        return clauses

    def _build_unary_counter(
        self,
        vars_list: list[int],
        alloc: _AuxVarAllocator,
    ) -> tuple[list[int], list[list[int]]]:
        """Build exact unary thermometer outputs out[t-1] <-> (sum(vars_list) >= t)."""
        m = len(vars_list)
        if m == 0:
            return [], []
        if m == 1:
            return [vars_list[0]], []

        clauses: list[list[int]] = []
        prev = [vars_list[0]]
        for i in range(1, m):
            x = vars_list[i]
            curr: list[int] = []
            # j = 1: curr[0] <-> (prev[0] OR x)
            c1 = alloc.alloc()
            clauses.append([-prev[0], c1])
            clauses.append([-x, c1])
            clauses.append([-c1, prev[0], x])
            curr.append(c1)

            # 2 <= j <= i: curr[j-1] <-> (prev[j-1] OR (prev[j-2] AND x))
            for j in range(2, i + 1):
                cj = alloc.alloc()
                p_same = prev[j - 1]
                p_prev = prev[j - 2]
                clauses.append([-p_same, cj])
                clauses.append([-p_prev, -x, cj])
                clauses.append([-cj, p_same, p_prev])
                clauses.append([-cj, p_same, x])
                curr.append(cj)

            # j = i + 1: curr[i] <-> (prev[i-1] AND x)
            c_top = alloc.alloc()
            clauses.append([-prev[i - 1], -x, c_top])
            clauses.append([-c_top, prev[i - 1]])
            clauses.append([-c_top, x])
            curr.append(c_top)
            prev = curr

        return prev, clauses

    def _encode_compare_counts(
        self,
        vars_a: list[int],
        vars_b: list[int],
        op: CompareOp,
        alloc: _AuxVarAllocator,
    ) -> list[list[int]]:
        """Encode count(vars_a) <op> count(vars_b) using exact unary counters."""
        a_ge, clauses_a = self._build_unary_counter(vars_a, alloc)
        b_ge, clauses_b = self._build_unary_counter(vars_b, alloc)
        clauses = clauses_a + clauses_b

        if op == CompareOp.EQ:
            clauses.extend(self._encode_unary_le(a_ge, b_ge))
            clauses.extend(self._encode_unary_le(b_ge, a_ge))
        elif op == CompareOp.LE:
            clauses.extend(self._encode_unary_le(a_ge, b_ge))
        elif op == CompareOp.GE:
            clauses.extend(self._encode_unary_le(b_ge, a_ge))
        elif op == CompareOp.LT:
            clauses.extend(self._encode_unary_lt(a_ge, b_ge))
        elif op == CompareOp.GT:
            clauses.extend(self._encode_unary_lt(b_ge, a_ge))
        else:
            raise ValueError(f"Unsupported CompareOp: {op!r}")
        return clauses

    @staticmethod
    def _encode_unary_le(a_ge: list[int], b_ge: list[int]) -> list[list[int]]:
        """Encode count(A) <= count(B) given thermometer vectors a_ge, b_ge."""
        m1, m2 = len(a_ge), len(b_ge)
        clauses: list[list[int]] = []
        for t in range(min(m1, m2)):
            clauses.append([-a_ge[t], b_ge[t]])
        if m1 > m2:
            # count(A) cannot reach m2 + 1
            clauses.append([-a_ge[m2]])
        return clauses

    @staticmethod
    def _encode_unary_lt(a_ge: list[int], b_ge: list[int]) -> list[list[int]]:
        """Encode count(A) < count(B) given thermometer vectors a_ge, b_ge."""
        m1, m2 = len(a_ge), len(b_ge)
        if m2 == 0:
            return [[]]
        clauses: list[list[int]] = [[b_ge[0]]]  # count(B) >= 1
        for t in range(min(m1, m2 - 1)):
            clauses.append([-a_ge[t], b_ge[t + 1]])
        if m1 >= m2:
            # count(A) cannot reach m2
            clauses.append([-a_ge[m2 - 1]])
        return clauses
