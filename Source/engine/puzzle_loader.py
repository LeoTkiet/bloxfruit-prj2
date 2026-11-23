"""JSON Puzzle Loader and internal hidden-world models (owned by TV1).

IMPORTANT ARCHITECTURAL BOUNDARY:
`HiddenCharacter` and `PuzzleDefinition` live strictly inside `engine/` and are
NEVER exposed through `IGameEngine.get_public_state()`. Only `GameEngine` holds
references to these hidden-world objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.contracts.models import (
    CellID,
    Clue,
    ClueType,
    CompareOp,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
    all_cell_ids,
)


class PuzzleLoadError(ValueError):
    """Raised when a puzzle JSON file cannot be read or parsed into structured objects."""


@dataclass(frozen=True)
class HiddenCharacter:
    """Private representation of a character card, including its hidden truth."""

    cell_id: CellID
    name: str
    profession: str
    hidden_status: Status
    hidden_clue: Clue


@dataclass(frozen=True)
class PuzzleDefinition:
    """Private complete puzzle definition owned exclusively by GameEngine."""

    puzzle_id: str
    name: str
    grid_size: int
    characters: tuple[HiddenCharacter, ...]  # deterministic row-major order
    initial_revealed: tuple[CellID, ...]
    difficulty: str = "medium"
    tags: tuple[str, ...] = ()
    expected_status: str = "SOLVABLE"  # SOLVABLE | AMBIGUOUS | INCONSISTENT

    @property
    def character_by_cell(self) -> dict[CellID, HiddenCharacter]:
        return {c.cell_id: c for c in self.characters}


def _require_key(data: dict[str, Any], key: str, context: str) -> Any:
    if key not in data:
        raise PuzzleLoadError(f"Missing required field {key!r} in {context}")
    return data[key]


def parse_region_spec(raw: dict[str, Any], context: str = "region") -> RegionSpec:
    """Parse a JSON dict into a frozen `RegionSpec`."""
    if not isinstance(raw, dict):
        raise PuzzleLoadError(f"{context} must be a JSON object, got {type(raw).__name__}")

    raw_type = _require_key(raw, "type", context)
    if not isinstance(raw_type, str):
        raise PuzzleLoadError(f"{context}.type must be a string")
    try:
        region_type = RegionType(raw_type.upper())
    except ValueError as exc:
        raise PuzzleLoadError(f"Unsupported region type {raw_type!r} in {context}") from exc

    if region_type == RegionType.ROW:
        row = _require_key(raw, "row", context)
        if not isinstance(row, int) or isinstance(row, bool):
            raise PuzzleLoadError(f"{context}.row must be an integer")
        return RegionSpec(region_type=region_type, row=row)

    if region_type == RegionType.COL:
        col = _require_key(raw, "col", context)
        if not isinstance(col, str):
            raise PuzzleLoadError(f"{context}.col must be a string")
        return RegionSpec(region_type=region_type, col=col.upper())

    if region_type == RegionType.NEIGHBORS:
        center = _require_key(raw, "center", context)
        if not isinstance(center, str):
            raise PuzzleLoadError(f"{context}.center must be a CellID string")
        return RegionSpec(region_type=region_type, center=center.upper())

    if region_type in (
        RegionType.EXPLICIT,
        RegionType.COMMON_NEIGHBORS,
        RegionType.BETWEEN,
    ):
        cells = _require_key(raw, "cells", context)
        if not isinstance(cells, list) or not all(isinstance(c, str) for c in cells):
            raise PuzzleLoadError(f"{context}.cells must be a list of CellID strings")
        return RegionSpec(
            region_type=region_type,
            cells=tuple(c.upper() for c in cells),
        )

    if region_type == RegionType.INTERSECTION:
        sub_raw = _require_key(raw, "sub_regions", context)
        if not isinstance(sub_raw, list):
            raise PuzzleLoadError(f"{context}.sub_regions must be a list")
        sub_regions = tuple(
            parse_region_spec(sr, context=f"{context}.sub_regions[{idx}]")
            for idx, sr in enumerate(sub_raw)
        )
        return RegionSpec(region_type=region_type, sub_regions=sub_regions)

    if region_type in (RegionType.CORNERS, RegionType.BOUNDARY):
        return RegionSpec(region_type=region_type)

    raise PuzzleLoadError(f"Unhandled region type {region_type!r}")


def _format_region_text(region: RegionSpec) -> str:
    """Generate a concise human-readable description of a RegionSpec."""
    rt = region.region_type
    if rt == RegionType.ROW:
        return f"row {region.row}"
    if rt == RegionType.COL:
        return f"column {region.col}"
    if rt == RegionType.NEIGHBORS:
        return f"neighbors of {region.center}"
    if rt == RegionType.EXPLICIT:
        return "{" + ", ".join(region.cells) + "}"
    if rt == RegionType.CORNERS:
        return "the corners"
    if rt == RegionType.BOUNDARY:
        return "the boundary"
    if rt == RegionType.COMMON_NEIGHBORS:
        return f"common neighbors of {region.cells[0]} and {region.cells[1]}"
    if rt == RegionType.BETWEEN:
        return f"cells between {region.cells[0]} and {region.cells[1]}"
    if rt == RegionType.INTERSECTION:
        parts = " ∩ ".join(_format_region_text(sr) for sr in region.sub_regions)
        return f"intersection({parts})"
    return str(rt.value)


def render_clue_text(clue: Clue) -> str:
    """Render natural-language fallback text for a structured Clue."""
    ct = clue.clue_type
    if ct == ClueType.FACT:
        label = "a Criminal" if clue.target_status == Status.CRIMINAL else "Innocent"
        return f"{clue.target} is {label}."
    if ct == ClueType.SAME:
        return f"{clue.targets[0]} and {clue.targets[1]} have the same status."
    if ct == ClueType.DIFFERENT:
        return f"{clue.targets[0]} and {clue.targets[1]} have different statuses."
    if ct == ClueType.EXACTLY and clue.region is not None:
        if clue.count == 0:
            return f"No one in {_format_region_text(clue.region)} is a Criminal."
        noun = "Criminal" if clue.count == 1 else "Criminals"
        return f"Exactly {clue.count} {noun} in {_format_region_text(clue.region)}."
    if ct == ClueType.AT_LEAST and clue.region is not None:
        noun = "Criminal" if clue.count == 1 else "Criminals"
        return f"At least {clue.count} {noun} in {_format_region_text(clue.region)}."
    if ct == ClueType.AT_MOST and clue.region is not None:
        noun = "Criminal" if clue.count == 1 else "Criminals"
        return f"At most {clue.count} {noun} in {_format_region_text(clue.region)}."
    if ct == ClueType.PARITY and clue.region is not None and clue.parity is not None:
        return (
            f"The number of Criminals in {_format_region_text(clue.region)} "
            f"is {clue.parity.value}."
        )
    if (
        ct == ClueType.COMPARE_COUNTS
        and clue.region is not None
        and clue.region_b is not None
        and clue.compare_op is not None
    ):
        op_words = {
            CompareOp.EQ: "the same number of Criminals as",
            CompareOp.LT: "fewer Criminals than",
            CompareOp.GT: "more Criminals than",
            CompareOp.LE: "at most as many Criminals as",
            CompareOp.GE: "at least as many Criminals as",
        }
        return (
            f"{_format_region_text(clue.region).capitalize()} has "
            f"{op_words[clue.compare_op]} {_format_region_text(clue.region_b)}."
        )
    return ""


def parse_clue(raw: dict[str, Any], owner: CellID, context: str = "clue") -> Clue:
    """Parse a JSON dict into a frozen `Clue`.

    Supports syntactic sugar `"type": "NO"` -> `ClueType.EXACTLY` with `count=0`.
    """
    if not isinstance(raw, dict):
        raise PuzzleLoadError(f"{context} must be a JSON object")

    clue_id = raw.get("clue_id", f"clue_{owner}")
    if not isinstance(clue_id, str) or not clue_id.strip():
        raise PuzzleLoadError(f"{context}.clue_id must be a non-empty string")

    raw_type = _require_key(raw, "type", context)
    if not isinstance(raw_type, str):
        raise PuzzleLoadError(f"{context}.type must be a string")
    raw_type_upper = raw_type.upper()

    # Spec Section 3.2: "The word NO may be rendered as EXACTLY(0, region)."
    is_no_alias = raw_type_upper == "NO"
    if is_no_alias:
        clue_type = ClueType.EXACTLY
    else:
        try:
            clue_type = ClueType(raw_type_upper)
        except ValueError as exc:
            raise PuzzleLoadError(f"Unsupported clue type {raw_type!r} in {context}") from exc

    raw_text = raw.get("text", "")
    if not isinstance(raw_text, str):
        raise PuzzleLoadError(f"{context}.text must be a string")

    clue: Clue
    if clue_type == ClueType.FACT:
        target = _require_key(raw, "target", context)
        raw_status = _require_key(raw, "target_status", context)
        if not isinstance(target, str) or not isinstance(raw_status, str):
            raise PuzzleLoadError(f"{context} FACT requires string target and target_status")
        try:
            target_status = Status(raw_status.upper())
        except ValueError as exc:
            raise PuzzleLoadError(f"Invalid target_status {raw_status!r} in {context}") from exc
        clue = Clue(
            clue_id=clue_id,
            owner=owner,
            clue_type=clue_type,
            target=target.upper(),
            target_status=target_status,
            text=raw_text,
        )

    elif clue_type in (ClueType.SAME, ClueType.DIFFERENT):
        targets = _require_key(raw, "targets", context)
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            raise PuzzleLoadError(f"{context}.targets must be a list of CellID strings")
        clue = Clue(
            clue_id=clue_id,
            owner=owner,
            clue_type=clue_type,
            targets=tuple(t.upper() for t in targets),
            text=raw_text,
        )

    elif clue_type in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
        region = parse_region_spec(_require_key(raw, "region", context), f"{context}.region")
        count = 0 if is_no_alias else _require_key(raw, "count", context)
        if not isinstance(count, int) or isinstance(count, bool):
            raise PuzzleLoadError(f"{context}.count must be an integer")
        clue = Clue(
            clue_id=clue_id,
            owner=owner,
            clue_type=clue_type,
            region=region,
            count=count,
            text=raw_text,
        )

    elif clue_type == ClueType.PARITY:
        region = parse_region_spec(_require_key(raw, "region", context), f"{context}.region")
        raw_parity = _require_key(raw, "parity", context)
        if not isinstance(raw_parity, str):
            raise PuzzleLoadError(f"{context}.parity must be a string ('EVEN' or 'ODD')")
        try:
            parity = ParityKind(raw_parity.upper())
        except ValueError as exc:
            raise PuzzleLoadError(f"Invalid parity {raw_parity!r} in {context}") from exc
        clue = Clue(
            clue_id=clue_id,
            owner=owner,
            clue_type=clue_type,
            region=region,
            parity=parity,
            text=raw_text,
        )

    elif clue_type == ClueType.COMPARE_COUNTS:
        region_a = parse_region_spec(_require_key(raw, "region", context), f"{context}.region")
        region_b = parse_region_spec(
            _require_key(raw, "region_b", context), f"{context}.region_b"
        )
        raw_op = _require_key(raw, "compare_op", context)
        if not isinstance(raw_op, str):
            raise PuzzleLoadError(f"{context}.compare_op must be a string")
        try:
            compare_op = CompareOp(raw_op.upper())
        except ValueError as exc:
            raise PuzzleLoadError(f"Invalid compare_op {raw_op!r} in {context}") from exc
        clue = Clue(
            clue_id=clue_id,
            owner=owner,
            clue_type=clue_type,
            region=region_a,
            region_b=region_b,
            compare_op=compare_op,
            text=raw_text,
        )
    else:
        raise PuzzleLoadError(f"Unhandled clue type {clue_type!r}")

    if not clue.text:
        clue = Clue(
            clue_id=clue.clue_id,
            owner=clue.owner,
            clue_type=clue.clue_type,
            target=clue.target,
            target_status=clue.target_status,
            targets=clue.targets,
            region=clue.region,
            region_b=clue.region_b,
            count=clue.count,
            parity=clue.parity,
            compare_op=clue.compare_op,
            text=render_clue_text(clue),
        )
    return clue


def load_puzzle_definition(path: str | Path) -> PuzzleDefinition:
    """Read and parse a puzzle JSON file into a `PuzzleDefinition`.

    Note: Call `validate_puzzle(definition)` after loading to check all domain
    and structural invariants (done automatically by `GameEngine.load_puzzle`).
    """
    file_path = Path(path)
    if not file_path.exists():
        raise PuzzleLoadError(f"Puzzle file not found: {file_path}")
    if not file_path.is_file():
        raise PuzzleLoadError(f"Puzzle path is not a file: {file_path}")

    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PuzzleLoadError(f"Invalid JSON in {file_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PuzzleLoadError(f"Puzzle root in {file_path} must be a JSON object")

    puzzle_id = _require_key(raw, "puzzle_id", "root")
    name = _require_key(raw, "name", "root")
    grid_size = _require_key(raw, "grid_size", "root")
    raw_chars = _require_key(raw, "characters", "root")
    raw_initial = _require_key(raw, "initial_revealed", "root")

    if not isinstance(puzzle_id, str) or not puzzle_id.strip():
        raise PuzzleLoadError("puzzle_id must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise PuzzleLoadError("name must be a non-empty string")
    if not isinstance(grid_size, int) or isinstance(grid_size, bool) or grid_size < 2 or grid_size > 26:
        raise PuzzleLoadError(f"grid_size must be an integer in [2, 26], got {grid_size!r}")
    if not isinstance(raw_chars, list):
        raise PuzzleLoadError("characters must be a list")
    if not isinstance(raw_initial, list) or not all(isinstance(c, str) for c in raw_initial):
        raise PuzzleLoadError("initial_revealed must be a list of CellID strings")

    parsed_chars: list[HiddenCharacter] = []
    for idx, ch in enumerate(raw_chars):
        ctx = f"characters[{idx}]"
        if not isinstance(ch, dict):
            raise PuzzleLoadError(f"{ctx} must be a JSON object")
        cell_id = _require_key(ch, "cell_id", ctx)
        ch_name = _require_key(ch, "name", ctx)
        profession = _require_key(ch, "profession", ctx)
        raw_status = _require_key(ch, "status", ctx)
        raw_clue = _require_key(ch, "clue", ctx)

        if not isinstance(cell_id, str):
            raise PuzzleLoadError(f"{ctx}.cell_id must be a string")
        if not isinstance(ch_name, str) or not ch_name.strip():
            raise PuzzleLoadError(f"{ctx}.name must be a non-empty string")
        if not isinstance(profession, str) or not profession.strip():
            raise PuzzleLoadError(f"{ctx}.profession must be a non-empty string")
        if not isinstance(raw_status, str):
            raise PuzzleLoadError(f"{ctx}.status must be a string")

        try:
            status = Status(raw_status.upper())
        except ValueError as exc:
            raise PuzzleLoadError(f"Invalid status {raw_status!r} in {ctx}") from exc

        cell_upper = cell_id.upper()
        clue = parse_clue(raw_clue, owner=cell_upper, context=f"{ctx}.clue")
        parsed_chars.append(
            HiddenCharacter(
                cell_id=cell_upper,
                name=ch_name.strip(),
                profession=profession.strip(),
                hidden_status=status,
                hidden_clue=clue,
            )
        )

    # Sort characters into deterministic row-major order when cell IDs are valid
    expected_order = {cid: idx for idx, cid in enumerate(all_cell_ids(grid_size))}
    parsed_chars.sort(key=lambda c: expected_order.get(c.cell_id, len(expected_order)))

    difficulty = str(raw.get("difficulty", "medium"))
    tags_raw = raw.get("tags", [])
    tags = tuple(str(t) for t in tags_raw) if isinstance(tags_raw, list) else ()
    expected_status = str(raw.get("expected_status", "SOLVABLE")).upper()

    return PuzzleDefinition(
        puzzle_id=puzzle_id.strip(),
        name=name.strip(),
        grid_size=grid_size,
        characters=tuple(parsed_chars),
        initial_revealed=tuple(c.upper() for c in raw_initial),
        difficulty=difficulty,
        tags=tags,
        expected_status=expected_status,
    )
