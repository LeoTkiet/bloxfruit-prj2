"""Mock `IGameEngine` and `ILogicAgent` implementations for independent GUI testing.

Allows TV5 to test 100% of GUI rendering, highlighting, manual verdicts,
error banners, Hint, Restart, Auto Solve, and Uniqueness without depending on
TV1, TV2, TV3, or TV4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from core.contracts.interfaces import IGameEngine
from core.contracts.models import (
    CellID,
    CharacterPublicInfo,
    Clue,
    ClueType,
    CNFStats,
    DeductionStep,
    HintResult,
    PublicState,
    RegionSpec,
    RegionType,
    SATMetrics,
    SATQueryLog,
    Status,
    UniquenessResult,
    VerdictCode,
    VerdictResponse,
)


def make_sample_3x3_clues() -> dict[CellID, Clue]:
    return {
        "A1": Clue(
            clue_id="clue_A1",
            owner="A1",
            clue_type=ClueType.EXACTLY,
            region=RegionSpec(region_type=RegionType.EXPLICIT, cells=("B1", "C2")),
            count=2,
            text="Exactly 2 Criminals in {B1, C2}.",
        ),
        "B1": Clue(
            clue_id="clue_B1",
            owner="B1",
            clue_type=ClueType.FACT,
            target="C1",
            target_status=Status.INNOCENT,
            text="C1 is Innocent.",
        ),
        "C1": Clue(
            clue_id="clue_C1",
            owner="C1",
            clue_type=ClueType.SAME,
            targets=("A2", "B2"),
            text="A2 and B2 have the same status.",
        ),
        "A2": Clue(
            clue_id="clue_A2",
            owner="A2",
            clue_type=ClueType.DIFFERENT,
            targets=("B2", "C2"),
            text="B2 and C2 have different statuses.",
        ),
        "B2": Clue(
            clue_id="clue_B2",
            owner="B2",
            clue_type=ClueType.AT_MOST,
            region=RegionSpec(region_type=RegionType.ROW, row=3),
            count=1,
            text="At most 1 Criminal in row 3.",
        ),
        "C2": Clue(
            clue_id="clue_C2",
            owner="C2",
            clue_type=ClueType.AT_LEAST,
            region=RegionSpec(region_type=RegionType.COL, col="A"),
            count=1,
            text="At least 1 Criminal in column A.",
        ),
        "A3": Clue(
            clue_id="clue_A3",
            owner="A3",
            clue_type=ClueType.FACT,
            target="A1",
            target_status=Status.INNOCENT,
            text="A1 is Innocent.",
        ),
        "B3": Clue(
            clue_id="clue_B3",
            owner="B3",
            clue_type=ClueType.FACT,
            target="B1",
            target_status=Status.CRIMINAL,
            text="B1 is Criminal.",
        ),
        "C3": Clue(
            clue_id="clue_C3",
            owner="C3",
            clue_type=ClueType.EXACTLY,
            region=RegionSpec(region_type=RegionType.COL, col="C"),
            count=1,
            text="Exactly 1 Criminal in column C.",
        ),
    }


class MockGameEngine:
    """Deterministic `IGameEngine` stub for unit testing the GUI in isolation."""

    def __init__(self) -> None:
        self._clues: dict[CellID, Clue] = make_sample_3x3_clues()
        self._names: dict[CellID, tuple[str, str]] = {
            "A1": ("Abel", "Astronaut"),
            "B1": ("Bea", "Cook"),
            "C1": ("Clara", "Guard"),
            "A2": ("Derek", "Cook"),
            "B2": ("Eliza", "Detective"),
            "C2": ("Franz", "Detective"),
            "A3": ("Grant", "Clerk"),
            "B3": ("Hannah", "Guard"),
            "C3": ("Ivy", "Clerk"),
        }
        self._solution: dict[CellID, Status] = {
            "A1": Status.INNOCENT,
            "B1": Status.CRIMINAL,
            "C1": Status.INNOCENT,
            "A2": Status.CRIMINAL,
            "B2": Status.INNOCENT,
            "C2": Status.CRIMINAL,
            "A3": Status.INNOCENT,
            "B3": Status.CRIMINAL,
            "C3": Status.INNOCENT,
        }
        self._highlight_map: dict[CellID, list[CellID]] = {
            "A1": ["B1", "C2"],
            "B1": ["C1"],
            "C3": ["C1", "C2", "C3"],
        }
        # Configurable responses per (cell, status) for testing all VerdictCodes
        self.verdict_overrides: dict[tuple[CellID, Status], VerdictCode] = {
            ("B1", Status.CRIMINAL): VerdictCode.ACCEPTED,
            ("B1", Status.INNOCENT): VerdictCode.CONTRADICTED,
            ("C1", Status.CRIMINAL): VerdictCode.NOT_PROVABLE,
            ("C1", Status.INNOCENT): VerdictCode.NOT_PROVABLE,
            ("A2", Status.CRIMINAL): VerdictCode.INCONSISTENT,
        }
        self.load_calls: list[Path] = []
        self.restart_calls: int = 0
        self.highlight_calls: list[CellID] = []
        self._revealed: set[CellID] = set()
        self._proved: dict[CellID, Status] = {}
        self._step: int = 0
        self._reset_initial()

    def _reset_initial(self) -> None:
        self._revealed = {"A1", "C3"}
        self._proved = {"A1": Status.INNOCENT, "C3": Status.INNOCENT}
        self._step = 0

    def load_puzzle(self, path: str | Path) -> PublicState:
        self.load_calls.append(Path(path))
        self._reset_initial()
        return self.get_public_state()

    def restart(self) -> PublicState:
        self.restart_calls += 1
        self._reset_initial()
        return self.get_public_state()

    def get_public_state(self) -> PublicState:
        chars: list[CharacterPublicInfo] = []
        revealed_clues: list[Clue] = []
        for cid in ("A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"):
            name, prof = self._names[cid]
            if cid in self._revealed:
                clue = self._clues[cid]
                chars.append(
                    CharacterPublicInfo(
                        cell_id=cid,
                        name=name,
                        profession=prof,
                        status=self._proved[cid],
                        is_revealed=True,
                        clue=clue,
                    )
                )
                revealed_clues.append(clue)
            else:
                chars.append(
                    CharacterPublicInfo(
                        cell_id=cid,
                        name=name,
                        profession=prof,
                        status=Status.UNKNOWN,
                        is_revealed=False,
                        clue=None,
                    )
                )
        return PublicState(
            puzzle_id="mock_3x3",
            puzzle_name="Mock 3x3 Precinct",
            grid_size=3,
            step=self._step,
            characters=tuple(chars),
            proved_verdicts=dict(self._proved),
            revealed_clues=tuple(revealed_clues),
            is_solved=(len(self._revealed) == 9),
        )

    def submit_verdict(self, cell: CellID, status: Status) -> VerdictResponse:
        code = self.verdict_overrides.get((cell, status))
        if code is None:
            # Default: accept if matching mock solution, else contradicted
            code = (
                VerdictCode.ACCEPTED
                if self._solution[cell] == status
                else VerdictCode.CONTRADICTED
            )

        if code == VerdictCode.ACCEPTED:
            self._revealed.add(cell)
            self._proved[cell] = status
            self._step += 1
            return VerdictResponse(
                code=VerdictCode.ACCEPTED,
                cell=cell,
                submitted_status=status,
                public_state=self.get_public_state(),
                revealed_clue=self._clues[cell],
                message=f"Accepted: {cell} is {status.value}.",
            )

        return VerdictResponse(
            code=code,
            cell=cell,
            submitted_status=status,
            public_state=self.get_public_state(),
            revealed_clue=None,
            message=f"Rejected ({code.value}) for {cell} as {status.value}.",
        )

    def get_highlighted_cells(self, cell: CellID) -> list[CellID]:
        self.highlight_calls.append(cell)
        if cell not in self._revealed:
            return []
        return list(self._highlight_map.get(cell, []))

    def get_all_clues_for_uniqueness(self) -> list[Clue]:
        return list(self._clues.values())


class MockGuiLogicAgent:
    """Configurable `ILogicAgent` stub supporting TV4's optional hooks."""

    def __init__(self) -> None:
        self.hint_to_return: HintResult = HintResult(
            cell="B1",
            forced_status=Status.CRIMINAL,
            relevant_clue_ids=("clue_A1",),
            message="B1 is forced to be CRIMINAL by clue_A1.",
            is_inconsistent=False,
        )
        self.auto_solve_mode: str = "SOLVED"  # "SOLVED" | "AMBIGUOUS" | "INCONSISTENT"
        self.uniqueness_to_return: UniquenessResult = UniquenessResult(
            is_unique=True,
            solution_count_status="UNIQUE",
        )
        self.clear_cache_calls: int = 0
        self.reset_stats_calls: int = 0

    def clear_cache(self) -> None:
        self.clear_cache_calls += 1

    def reset_stats(self) -> None:
        self.reset_stats_calls += 1

    def check_consistency(self, state: PublicState) -> bool:
        return self.auto_solve_mode != "INCONSISTENT"

    def classify_character(self, state: PublicState, cell: CellID) -> Status:
        return Status.UNKNOWN

    def classify_all(self, state: PublicState) -> dict[CellID, Status]:
        return {c: Status.UNKNOWN for c in state.unsolved_cells}

    def get_hint(self, state: PublicState) -> HintResult:
        return self.hint_to_return

    def run_auto_solve(
        self,
        engine: IGameEngine,
        on_step: Optional[Callable[[DeductionStep], None]] = None,
    ) -> list[DeductionStep]:
        steps: list[DeductionStep] = []
        if self.auto_solve_mode == "AMBIGUOUS":
            state = engine.get_public_state()
            term = DeductionStep(
                step_number=state.step + 1,
                active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                sat_queries=(
                    SATQueryLog(
                        cell="B1",
                        assumptions=(-2,),
                        is_sat=True,
                        metrics=SATMetrics(
                            decisions=1, propagations=3, backtracks=0, runtime_ms=0.5
                        ),
                    ),
                ),
                cell=None,
                verdict=Status.UNKNOWN,
                verdict_code=VerdictCode.NOT_PROVABLE,
                cnf_stats=CNFStats(
                    num_primary_vars=9, num_aux_vars=0, num_clauses=8
                ),
            )
            steps.append(term)
            if on_step:
                on_step(term)
            return steps

        if self.auto_solve_mode == "INCONSISTENT":
            state = engine.get_public_state()
            term = DeductionStep(
                step_number=state.step + 1,
                active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                sat_queries=(),
                cell=None,
                verdict=Status.UNKNOWN,
                verdict_code=VerdictCode.INCONSISTENT,
                cnf_stats=CNFStats(
                    num_primary_vars=9, num_aux_vars=0, num_clauses=10
                ),
            )
            steps.append(term)
            if on_step:
                on_step(term)
            return steps

        # SOLVED mode: solve all remaining cells in MockGameEngine
        sol: Mapping[CellID, Status] = getattr(engine, "_solution", {})
        while True:
            state = engine.get_public_state()
            if state.is_solved or not state.unsolved_cells:
                break
            cid = state.unsolved_cells[0]
            verdict = sol.get(cid, Status.INNOCENT)
            # Ensure MockGameEngine accepts during auto solve
            if hasattr(engine, "verdict_overrides"):
                engine.verdict_overrides[(cid, verdict)] = VerdictCode.ACCEPTED
            resp = engine.submit_verdict(cid, verdict)
            step = DeductionStep(
                step_number=resp.public_state.step,
                active_clue_ids=tuple(c.clue_id for c in state.revealed_clues),
                sat_queries=(
                    SATQueryLog(
                        cell=cid,
                        assumptions=(-1,),
                        is_sat=False,
                        metrics=SATMetrics(
                            decisions=1, propagations=4, backtracks=1, runtime_ms=0.4
                        ),
                    ),
                    SATQueryLog(
                        cell=cid,
                        assumptions=(1,),
                        is_sat=True,
                        metrics=SATMetrics(),
                        cached=True,
                    ),
                ),
                cell=cid,
                verdict=verdict,
                verdict_code=resp.code,
                revealed_clue=resp.revealed_clue,
                cnf_stats=CNFStats(
                    num_primary_vars=9, num_aux_vars=2, num_clauses=14
                ),
            )
            steps.append(step)
            if on_step:
                on_step(step)
            if resp.code != VerdictCode.ACCEPTED:
                break
        return steps

    def check_uniqueness(
        self,
        clues: Sequence[Clue],
        grid_size: int,
    ) -> UniquenessResult:
        return self.uniqueness_to_return
