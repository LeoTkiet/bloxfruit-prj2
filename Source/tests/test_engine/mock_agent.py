"""Mock & Exact-Oracle ILogicAgent implementations for TV1's independent tests.

Allows TV1 to fully test `GameEngine` and verify all 15 puzzles in Week 1
without depending on TV2 (logic/), TV3 (solver/), or TV4 (agent/).
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from core.contracts.interfaces import IGameEngine
from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CompareOp,
    DeductionStep,
    HintResult,
    ParityKind,
    PublicState,
    Status,
    UniquenessResult,
    VerdictCode,
    all_cell_ids,
)
from engine.puzzle_validator import resolve_region_cells


class MockLogicAgent:
    """Configurable stub implementing `ILogicAgent` for deterministic GameEngine unit tests."""

    def __init__(
        self,
        *,
        consistent: bool = True,
        entailed: Optional[Mapping[CellID, Status]] = None,
    ) -> None:
        self.consistent: bool = consistent
        self.entailed: dict[CellID, Status] = dict(entailed or {})
        self.received_states: list[PublicState] = []
        self.consistency_calls: int = 0
        self.classify_calls: list[CellID] = []

    def check_consistency(self, state: PublicState) -> bool:
        self.received_states.append(state)
        self.consistency_calls += 1
        return self.consistent

    def classify_character(self, state: PublicState, cell: CellID) -> Status:
        self.received_states.append(state)
        self.classify_calls.append(cell)
        return self.entailed.get(cell, Status.UNKNOWN)

    def classify_all(self, state: PublicState) -> dict[CellID, Status]:
        self.received_states.append(state)
        return {
            cid: self.entailed.get(cid, Status.UNKNOWN)
            for cid in state.unsolved_cells
        }

    def get_hint(self, state: PublicState) -> HintResult:
        self.received_states.append(state)
        if not self.consistent:
            return HintResult(
                cell=None,
                forced_status=Status.UNKNOWN,
                message="KB is inconsistent",
                is_inconsistent=True,
            )
        for cid in state.unsolved_cells:
            st = self.entailed.get(cid, Status.UNKNOWN)
            if st != Status.UNKNOWN:
                return HintResult(
                    cell=cid,
                    forced_status=st,
                    relevant_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                    message=f"Mock hint: {cid} is {st.value}",
                )
        return HintResult(
            cell=None,
            forced_status=Status.UNKNOWN,
            message="No forced move available",
        )

    def run_auto_solve(self, engine: IGameEngine) -> list[DeductionStep]:
        steps: list[DeductionStep] = []
        while True:
            state = engine.get_public_state()
            if state.is_solved:
                break
            if not self.check_consistency(state):
                steps.append(
                    DeductionStep(
                        step_number=state.step + 1,
                        active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                        sat_queries=(),
                        cell=None,
                        verdict=Status.UNKNOWN,
                        verdict_code=VerdictCode.INCONSISTENT,
                    )
                )
                break
            chosen: Optional[tuple[CellID, Status]] = None
            for cid in state.unsolved_cells:
                st = self.classify_character(state, cid)
                if st != Status.UNKNOWN:
                    chosen = (cid, st)
                    break
            if chosen is None:
                steps.append(
                    DeductionStep(
                        step_number=state.step + 1,
                        active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                        sat_queries=(),
                        cell=None,
                        verdict=Status.UNKNOWN,
                        verdict_code=VerdictCode.NOT_PROVABLE,
                    )
                )
                break
            resp = engine.submit_verdict(chosen[0], chosen[1])
            steps.append(
                DeductionStep(
                    step_number=resp.public_state.step,
                    active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                    sat_queries=(),
                    cell=chosen[0],
                    verdict=chosen[1],
                    verdict_code=resp.code,
                    revealed_clue=resp.revealed_clue,
                )
            )
            if resp.code != VerdictCode.ACCEPTED:
                break
        return steps

    def check_uniqueness(
        self,
        clues: Sequence[Clue],
        grid_size: int,
    ) -> UniquenessResult:
        return UniquenessResult(is_unique=True, solution_count_status="UNIQUE")


# ---------------------------------------------------------------------------
# Exact Reference Constraint Oracle (used solely in test_puzzle_solvability.py)
# ---------------------------------------------------------------------------


def evaluate_clue_truth(
    clue: Clue,
    assignment: Mapping[CellID, bool],
    grid_size: int,
) -> bool:
    """Direct semantic evaluation of a clue on a complete assignment (True=Criminal)."""
    ct = clue.clue_type
    if ct == ClueType.FACT:
        assert clue.target is not None
        return assignment[clue.target] == (clue.target_status == Status.CRIMINAL)
    if ct == ClueType.SAME:
        return assignment[clue.targets[0]] == assignment[clue.targets[1]]
    if ct == ClueType.DIFFERENT:
        return assignment[clue.targets[0]] != assignment[clue.targets[1]]
    if ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
        assert clue.region is not None and clue.count is not None
        cells = resolve_region_cells(clue.region, grid_size)
        cnt = sum(1 for c in cells if assignment[c])
        if ct == ClueType.EXACTLY:
            return cnt == clue.count
        if ct == ClueType.AT_LEAST:
            return cnt >= clue.count
        return cnt <= clue.count
    if ct == ClueType.PARITY:
        assert clue.region is not None and clue.parity is not None
        cells = resolve_region_cells(clue.region, grid_size)
        cnt = sum(1 for c in cells if assignment[c])
        return (cnt % 2 == 0) if clue.parity == ParityKind.EVEN else (cnt % 2 == 1)
    if ct == ClueType.COMPARE_COUNTS:
        assert clue.region is not None and clue.region_b is not None and clue.compare_op is not None
        c1 = sum(1 for c in resolve_region_cells(clue.region, grid_size) if assignment[c])
        c2 = sum(1 for c in resolve_region_cells(clue.region_b, grid_size) if assignment[c])
        op = clue.compare_op
        if op == CompareOp.EQ:
            return c1 == c2
        if op == CompareOp.LT:
            return c1 < c2
        if op == CompareOp.GT:
            return c1 > c2
        if op == CompareOp.LE:
            return c1 <= c2
        if op == CompareOp.GE:
            return c1 >= c2
    raise ValueError(f"Unsupported clue type: {ct}")


class _Constraint:
    def __init__(self, clue: Clue, grid_size: int) -> None:
        self.clue = clue
        self.ct = clue.clue_type
        self.cells_a: tuple[CellID, ...] = ()
        self.cells_b: tuple[CellID, ...] = ()
        if self.ct == ClueType.FACT:
            assert clue.target is not None
            self.cells_a = (clue.target,)
            self.want = clue.target_status == Status.CRIMINAL
        elif self.ct in (ClueType.SAME, ClueType.DIFFERENT):
            self.cells_a = clue.targets
        elif self.ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST, ClueType.PARITY):
            assert clue.region is not None
            self.cells_a = tuple(resolve_region_cells(clue.region, grid_size))
        elif self.ct == ClueType.COMPARE_COUNTS:
            assert clue.region is not None and clue.region_b is not None
            self.cells_a = tuple(resolve_region_cells(clue.region, grid_size))
            self.cells_b = tuple(resolve_region_cells(clue.region_b, grid_size))
        self.all_vars: tuple[CellID, ...] = tuple(dict.fromkeys(self.cells_a + self.cells_b))

    def propagate(self, assign: dict[CellID, bool]) -> tuple[bool, list[tuple[CellID, bool]]]:
        ct = self.ct
        if ct == ClueType.FACT:
            c = self.cells_a[0]
            if c in assign:
                return (assign[c] == self.want, [])
            return (True, [(c, self.want)])

        if ct in (ClueType.SAME, ClueType.DIFFERENT):
            a, b = self.cells_a
            same = ct == ClueType.SAME
            in_a, in_b = a in assign, b in assign
            if in_a and in_b:
                return ((assign[a] == assign[b]) if same else (assign[a] != assign[b]), [])
            if in_a:
                return (True, [(b, assign[a] if same else (not assign[a]))])
            if in_b:
                return (True, [(a, assign[b] if same else (not assign[b]))])
            return (True, [])

        if ct in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
            trues = sum(1 for c in self.cells_a if assign.get(c) is True)
            unassigned = [c for c in self.cells_a if c not in assign]
            assert self.clue.count is not None
            k = self.clue.count
            u = len(unassigned)
            if ct == ClueType.EXACTLY:
                if trues > k or trues + u < k:
                    return (False, [])
                if trues == k and u:
                    return (True, [(c, False) for c in unassigned])
                if trues + u == k and u:
                    return (True, [(c, True) for c in unassigned])
                return (True, [])
            if ct == ClueType.AT_LEAST:
                if trues + u < k:
                    return (False, [])
                if trues + u == k and u:
                    return (True, [(c, True) for c in unassigned])
                return (True, [])
            if trues > k:
                return (False, [])
            if trues == k and u:
                return (True, [(c, False) for c in unassigned])
            return (True, [])

        if ct == ClueType.PARITY:
            trues = sum(1 for c in self.cells_a if assign.get(c) is True)
            unassigned = [c for c in self.cells_a if c not in assign]
            want_odd = self.clue.parity == ParityKind.ODD
            if not unassigned:
                return ((trues % 2 == 1) == want_odd, [])
            if len(unassigned) == 1:
                return (True, [(unassigned[0], (trues % 2 == 1) != want_odd)])
            return (True, [])

        if ct == ClueType.COMPARE_COUNTS:
            t1 = sum(1 for c in self.cells_a if assign.get(c) is True)
            u1 = sum(1 for c in self.cells_a if c not in assign)
            t2 = sum(1 for c in self.cells_b if assign.get(c) is True)
            u2 = sum(1 for c in self.cells_b if c not in assign)
            min1, max1, min2, max2 = t1, t1 + u1, t2, t2 + u2
            op = self.clue.compare_op
            if op == CompareOp.EQ and (max1 < min2 or max2 < min1):
                return (False, [])
            if op == CompareOp.LT and min1 >= max2:
                return (False, [])
            if op == CompareOp.GT and max1 <= min2:
                return (False, [])
            if op == CompareOp.LE and min1 > max2:
                return (False, [])
            if op == CompareOp.GE and max1 < min2:
                return (False, [])
            return (True, [])
        raise ValueError(f"Unhandled clue type: {ct}")


def _find_model(
    grid_size: int,
    constraints: list[_Constraint],
    fixed: dict[CellID, bool],
    blocking: Optional[dict[CellID, bool]] = None,
) -> Optional[dict[CellID, bool]]:
    cells = list(all_cell_ids(grid_size))
    var_to_cons: dict[CellID, list[_Constraint]] = {c: [] for c in cells}
    for con in constraints:
        for v in con.all_vars:
            var_to_cons[v].append(con)

    def propagate_all(assign: dict[CellID, bool], seed_cons: list[_Constraint]) -> bool:
        queue = list(seed_cons)
        in_q = {id(c) for c in queue}
        while queue:
            con = queue.pop()
            in_q.discard(id(con))
            ok, forced = con.propagate(assign)
            if not ok:
                return False
            for var, val in forced:
                if var in assign:
                    if assign[var] != val:
                        return False
                else:
                    assign[var] = val
                    for dep in var_to_cons[var]:
                        if id(dep) not in in_q:
                            queue.append(dep)
                            in_q.add(id(dep))
        return True

    root = dict(fixed)
    if not propagate_all(root, constraints):
        return None

    var_order = sorted(cells, key=lambda c: (-len(var_to_cons[c]), cells.index(c)))

    def search(assign: dict[CellID, bool]) -> Optional[dict[CellID, bool]]:
        if len(assign) == len(cells):
            if blocking is not None and all(assign[c] == blocking[c] for c in cells):
                return None
            return assign
        branch_var = next(v for v in var_order if v not in assign)
        for val in (True, False):
            nxt = dict(assign)
            nxt[branch_var] = val
            if propagate_all(nxt, var_to_cons[branch_var]):
                res = search(nxt)
                if res is not None:
                    return res
        return None

    return search(root)


class ExactTestOracleAgent:
    """Exact no-guess oracle implementing `ILogicAgent` strictly from `PublicState`.

    Used ONLY inside `tests/test_engine/test_puzzle_solvability.py` to prove that
    TV1's puzzle dataset is 100% unique and no-guess solvable end-to-end through
    `GameEngine`. (TV4 owns the real CNF+DPLL `DeductiveLogicAgent` in `agent/`.)
    """

    def _proved_bool(self, state: PublicState) -> dict[CellID, bool]:
        return {
            cid: (st == Status.CRIMINAL)
            for cid, st in state.proved_verdicts.items()
        }

    def check_consistency(self, state: PublicState) -> bool:
        cons = [_Constraint(c, state.grid_size) for c in state.revealed_clues]
        return _find_model(state.grid_size, cons, self._proved_bool(state)) is not None

    def classify_character(self, state: PublicState, cell: CellID) -> Status:
        cons = [_Constraint(c, state.grid_size) for c in state.revealed_clues]
        proved = self._proved_bool(state)
        if _find_model(state.grid_size, cons, {**proved, cell: False}) is None:
            return Status.CRIMINAL
        if _find_model(state.grid_size, cons, {**proved, cell: True}) is None:
            return Status.INNOCENT
        return Status.UNKNOWN

    def classify_all(self, state: PublicState) -> dict[CellID, Status]:
        cons = [_Constraint(c, state.grid_size) for c in state.revealed_clues]
        proved = self._proved_bool(state)
        base = _find_model(state.grid_size, cons, proved)
        if base is None:
            return {}
        seen_t = {c for c, v in base.items() if v}
        seen_f = {c for c, v in base.items() if not v}
        out: dict[CellID, Status] = {}
        for cid in state.unsolved_cells:
            if cid not in seen_f:
                m = _find_model(state.grid_size, cons, {**proved, cid: False})
                if m is None:
                    out[cid] = Status.CRIMINAL
                    continue
                for k, v in m.items():
                    (seen_t if v else seen_f).add(k)
            if cid not in seen_t:
                m = _find_model(state.grid_size, cons, {**proved, cid: True})
                if m is None:
                    out[cid] = Status.INNOCENT
                    continue
                for k, v in m.items():
                    (seen_t if v else seen_f).add(k)
            out[cid] = Status.UNKNOWN
        return out

    def get_hint(self, state: PublicState) -> HintResult:
        if not self.check_consistency(state):
            return HintResult(None, Status.UNKNOWN, is_inconsistent=True)
        classes = self.classify_all(state)
        for cid in state.unsolved_cells:
            if classes[cid] != Status.UNKNOWN:
                return HintResult(cid, classes[cid])
        return HintResult(None, Status.UNKNOWN)

    def run_auto_solve(self, engine: IGameEngine) -> list[DeductionStep]:
        trace: list[DeductionStep] = []
        while True:
            state = engine.get_public_state()
            if state.is_solved:
                break
            if not self.check_consistency(state):
                trace.append(
                    DeductionStep(
                        step_number=state.step + 1,
                        active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                        sat_queries=(),
                        cell=None,
                        verdict=Status.UNKNOWN,
                        verdict_code=VerdictCode.INCONSISTENT,
                    )
                )
                break
            classes = self.classify_all(state)
            forced = [
                (cid, classes[cid])
                for cid in state.unsolved_cells
                if classes[cid] != Status.UNKNOWN
            ]
            if not forced:
                trace.append(
                    DeductionStep(
                        step_number=state.step + 1,
                        active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                        sat_queries=(),
                        cell=None,
                        verdict=Status.UNKNOWN,
                        verdict_code=VerdictCode.NOT_PROVABLE,
                    )
                )
                break
            cell, verdict = forced[0]
            resp = engine.submit_verdict(cell, verdict)
            trace.append(
                DeductionStep(
                    step_number=resp.public_state.step,
                    active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                    sat_queries=(),
                    cell=cell,
                    verdict=verdict,
                    verdict_code=resp.code,
                    revealed_clue=resp.revealed_clue,
                )
            )
            if resp.code != VerdictCode.ACCEPTED:
                break
        return trace

    def check_uniqueness(
        self,
        clues: Sequence[Clue],
        grid_size: int,
    ) -> UniquenessResult:
        cons = [_Constraint(c, grid_size) for c in clues]
        m1 = _find_model(grid_size, cons, {})
        if m1 is None:
            return UniquenessResult(is_unique=False, solution_count_status="UNSAT")
        m2 = _find_model(grid_size, cons, {}, blocking=m1)
        to_status = lambda m: {
            k: (Status.CRIMINAL if v else Status.INNOCENT) for k, v in m.items()
        }
        if m2 is None:
            return UniquenessResult(
                is_unique=True,
                solution_count_status="UNIQUE",
                first_model=to_status(m1),
            )
        return UniquenessResult(
            is_unique=False,
            solution_count_status="MULTIPLE",
            first_model=to_status(m1),
            second_model=to_status(m2),
        )
