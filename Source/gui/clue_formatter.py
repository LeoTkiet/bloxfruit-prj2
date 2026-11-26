"""Natural-language formatter for structured Griductive clues and regions.

Prefers `clue.text` when present in the puzzle JSON, and automatically generates
a concise, readable English description for every core clue template and
extension when `clue.text` is empty.
"""

from __future__ import annotations

from core.contracts.models import (
    Clue,
    ClueType,
    CompareOp,
    ParityKind,
    RegionSpec,
    RegionType,
    Status,
)


def _plural_criminal(count: int) -> str:
    return "Criminal" if count == 1 else "Criminals"


def format_region(region: RegionSpec) -> str:
    """Render a `RegionSpec` into concise natural language."""
    rt = region.region_type
    if rt == RegionType.ROW:
        return f"row {region.row}"
    if rt == RegionType.COL:
        return f"column {region.col}"
    if rt == RegionType.NEIGHBORS:
        return f"neighbors of {region.center}"
    if rt == RegionType.EXPLICIT:
        return "{" + ", ".join(region.cells) + "}"
    if rt == RegionType.INTERSECTION:
        parts = [format_region(sub) for sub in region.sub_regions]
        return "(" + " ∩ ".join(parts) + ")"
    if rt == RegionType.COMMON_NEIGHBORS:
        if len(region.cells) == 2:
            return f"common neighbors of {region.cells[0]} & {region.cells[1]}"
        return f"common neighbors of {', '.join(region.cells)}"
    if rt == RegionType.CORNERS:
        return "the 4 corners"
    if rt == RegionType.BOUNDARY:
        return "the boundary"
    if rt == RegionType.BETWEEN:
        if len(region.cells) == 2:
            return f"cells between {region.cells[0]} and {region.cells[1]}"
        return f"cells between {', '.join(region.cells)}"
    return rt.value


def format_clue(clue: Clue) -> str:
    """Return a clean natural-language string describing a revealed `Clue`."""
    if clue.text and clue.text.strip():
        return clue.text.strip()

    ct = clue.clue_type
    if ct == ClueType.FACT:
        label = (
            "Criminal"
            if clue.target_status == Status.CRIMINAL
            else "Innocent"
            if clue.target_status == Status.INNOCENT
            else "Unknown"
        )
        return f"{clue.target} is {label}."

    if ct == ClueType.SAME:
        a, b = clue.targets[0], clue.targets[1]
        return f"{a} and {b} have the same status."

    if ct == ClueType.DIFFERENT:
        a, b = clue.targets[0], clue.targets[1]
        return f"{a} and {b} have different statuses."

    if ct == ClueType.EXACTLY:
        assert clue.region is not None and clue.count is not None
        reg = format_region(clue.region)
        if clue.count == 0:
            return f"No Criminals in {reg}."
        return f"Exactly {clue.count} {_plural_criminal(clue.count)} in {reg}."

    if ct == ClueType.AT_LEAST:
        assert clue.region is not None and clue.count is not None
        reg = format_region(clue.region)
        return f"At least {clue.count} {_plural_criminal(clue.count)} in {reg}."

    if ct == ClueType.AT_MOST:
        assert clue.region is not None and clue.count is not None
        reg = format_region(clue.region)
        return f"At most {clue.count} {_plural_criminal(clue.count)} in {reg}."

    if ct == ClueType.PARITY:
        assert clue.region is not None and clue.parity is not None
        reg = format_region(clue.region)
        kind = "even" if clue.parity == ParityKind.EVEN else "odd"
        return f"An {kind} number of Criminals in {reg}."

    if ct == ClueType.COMPARE_COUNTS:
        assert (
            clue.region is not None
            and clue.region_b is not None
            and clue.compare_op is not None
        )
        left = format_region(clue.region)
        right = format_region(clue.region_b)
        op_phrase = {
            CompareOp.EQ: "the same number of Criminals as",
            CompareOp.LT: "fewer Criminals than",
            CompareOp.GT: "more Criminals than",
            CompareOp.LE: "at most as many Criminals as",
            CompareOp.GE: "at least as many Criminals as",
        }[clue.compare_op]
        return f"{left.capitalize()} has {op_phrase} {right}."

    return f"[{ct.value}] ({clue.clue_id})"
