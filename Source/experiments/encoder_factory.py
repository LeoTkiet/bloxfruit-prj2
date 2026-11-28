"""Factory resolving TV2's real CNF encoder with safe StubCNFEncoder fallback."""

from __future__ import annotations

import importlib
import inspect
import logging
import warnings
from dataclasses import dataclass
from typing import Optional

from core.contracts.interfaces import ICNFEncoder
from experiments.stub_encoder import StubCNFEncoder

logger = logging.getLogger("experiments")

# Single-line override once TV2 finalizes class path, e.g. "logic.cnf_encoder:CNFEncoder"
REAL_ENCODER_SPEC: Optional[str] = "logic.cnf_encoder:CNFEncoder"

_CANDIDATE_ENCODERS: tuple[tuple[str, str], ...] = (
    ("logic.cnf_encoder", "CNFEncoder"),
    ("logic", "CNFEncoder"),
    ("logic.encoder", "CNFEncoder"),
    ("logic.cnf_encoder", "GriductiveCNFEncoder"),
)


@dataclass(frozen=True)
class EncoderSelection:
    """Resolved encoder (or skip reason when Sinz requires TV2's real encoder)."""

    encoder: Optional[ICNFEncoder]
    effective_encoding: str
    is_stub: bool
    skipped_reason: Optional[str] = None


def _instantiate_real_encoder(cls: type, strategy: str) -> Optional[ICNFEncoder]:
    """Instantiate `cls` with `strategy` if its constructor supports it."""
    try:
        sig = inspect.signature(cls.__init__)
    except (TypeError, ValueError):
        return None

    params = sig.parameters
    for kw in ("cardinality_encoding", "encoding", "strategy", "mode"):
        if kw in params:
            try:
                inst = cls(**{kw: strategy})
                if isinstance(inst, ICNFEncoder):
                    return inst
            except (TypeError, ValueError):
                return None

    # Positional / zero-arg fallback only valid for direct if no strategy param exists
    if strategy == "direct":
        try:
            inst = cls()
            if isinstance(inst, ICNFEncoder):
                return inst
        except TypeError:
            return None
    return None


def _try_load_real_encoder(strategy: str) -> Optional[ICNFEncoder]:
    candidates: list[tuple[str, str]] = []
    if REAL_ENCODER_SPEC:
        mod_name, _, attr_name = REAL_ENCODER_SPEC.partition(":")
        if mod_name and attr_name:
            candidates.append((mod_name, attr_name))
    candidates.extend(_CANDIDATE_ENCODERS)

    for mod_name, attr_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        cls = getattr(mod, attr_name, None)
        if cls is None or not isinstance(cls, type):
            continue
        inst = _instantiate_real_encoder(cls, strategy)
        if inst is not None:
            return inst
    return None


def make_encoder(strategy: str) -> EncoderSelection:
    """Build an `ICNFEncoder` for `strategy` ('direct' or 'sinz').

    - Uses TV2's real encoder from `logic/` if available and supporting `strategy`.
    - Otherwise, `strategy='direct'` falls back to `StubCNFEncoder` with a warning
      and reports `effective_encoding='stub'`.
    - `strategy='sinz'` without a real encoder returns `encoder=None` with
      `skipped_reason` so benchmark rows record `SKIPPED_NO_ENCODER` cleanly.
    """
    if strategy not in ("direct", "sinz"):
        raise ValueError(f"Unsupported encoding strategy {strategy!r}")

    real = _try_load_real_encoder(strategy)
    if real is not None:
        return EncoderSelection(
            encoder=real,
            effective_encoding=strategy,
            is_stub=False,
            skipped_reason=None,
        )

    if strategy == "direct":
        msg = (
            "Real TV2 encoder not found in `logic/`; falling back to temporary "
            "StubCNFEncoder (encoding='stub'). Do NOT use stub figures in final report."
        )
        logger.warning(msg)
        warnings.warn(msg, UserWarning, stacklevel=2)
        return EncoderSelection(
            encoder=StubCNFEncoder(),
            effective_encoding="stub",
            is_stub=True,
            skipped_reason=None,
        )

    return EncoderSelection(
        encoder=None,
        effective_encoding="sinz",
        is_stub=False,
        skipped_reason="No real TV2 Sinz encoder available in logic/",
    )
