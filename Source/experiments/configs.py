"""Experiment configuration matrix (C0-C7 and full 24-config grid)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Optional, Sequence

VALID_ENCODINGS = ("direct", "sinz")
VALID_HEURISTICS = ("lexicographic", "moms", "jw")


@dataclass(frozen=True)
class ExperimentConfig:
    """Single benchmark configuration across encoder, DPLL, and agent axes."""

    config_id: str
    name: str
    encoding: str
    heuristic: str
    pure_literal: bool
    model_caching: bool


def get_core_configs(best_heur: str = "jw") -> list[ExperimentConfig]:
    """Return the 8 core ablation configurations C0-C7."""
    if best_heur not in VALID_HEURISTICS:
        raise ValueError(
            f"Invalid best_heur {best_heur!r}; expected one of {VALID_HEURISTICS}"
        )
    return [
        ExperimentConfig("C0", "baseline_direct", "direct", "lexicographic", False, False),
        ExperimentConfig("C1", "direct_pl", "direct", "lexicographic", True, False),
        ExperimentConfig("C2", "direct_pl_moms", "direct", "moms", True, False),
        ExperimentConfig("C3", "direct_pl_jw", "direct", "jw", True, False),
        ExperimentConfig("C4", "direct_cache", "direct", "lexicographic", False, True),
        ExperimentConfig("C5", "baseline_sinz", "sinz", "lexicographic", False, False),
        ExperimentConfig("C6", "opt_direct", "direct", best_heur, True, True),
        ExperimentConfig("C7", "opt_sinz", "sinz", best_heur, True, True),
    ]


def get_full_grid_configs(best_heur: str = "jw") -> list[ExperimentConfig]:
    """Return all 24 factorial combinations (2 encodings x 3 heuristics x 2 PL x 2 cache)."""
    core = get_core_configs(best_heur=best_heur)
    core_by_tuple = {
        (c.encoding, c.heuristic, c.pure_literal, c.model_caching): c
        for c in core
    }

    configs: list[ExperimentConfig] = list(core)
    extra_idx = 8
    for enc, heur, pl, mc in product(
        VALID_ENCODINGS, VALID_HEURISTICS, (False, True), (False, True)
    ):
        key = (enc, heur, pl, mc)
        if key in core_by_tuple:
            continue
        pl_tag = "pl" if pl else "nopl"
        mc_tag = "cache" if mc else "nocache"
        cid = f"G{extra_idx:02d}"
        name = f"{enc}_{heur}_{pl_tag}_{mc_tag}"
        configs.append(ExperimentConfig(cid, name, enc, heur, pl, mc))
        extra_idx += 1

    return configs


def select_configs(
    config_ids: Optional[Sequence[str]] = None,
    *,
    best_heur: str = "jw",
    full_grid: bool = False,
) -> list[ExperimentConfig]:
    """Select configurations from C0-C7 or the full 24-config grid."""
    pool = (
        get_full_grid_configs(best_heur=best_heur)
        if full_grid
        else get_core_configs(best_heur=best_heur)
    )
    if not config_ids:
        return pool

    by_id = {c.config_id: c for c in pool}
    selected: list[ExperimentConfig] = []
    for cid in config_ids:
        cid_norm = cid.strip()
        if not cid_norm:
            continue
        if cid_norm not in by_id:
            raise ValueError(
                f"Unknown config_id {cid_norm!r}. Available: {list(by_id.keys())}"
            )
        selected.append(by_id[cid_norm])
    return selected
