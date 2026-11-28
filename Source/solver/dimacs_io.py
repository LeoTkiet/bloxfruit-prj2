"""DIMACS CNF format serialization and deserialization utility.

This module provides standard DIMACS CNF file parsing and writing:
- `parse_dimacs_cnf`: parse a DIMACS formatted string into clauses and var count.
- `read_dimacs_file`: read a `.cnf` file into a `CNFFormula`.
- `to_dimacs_string`: format a `CNFFormula` into a standard DIMACS string.
- `write_dimacs_file`: write a `CNFFormula` to a `.cnf` file on disk.

Format reference:
- Lines starting with 'c' are comments.
- Problem line: 'p cnf <nbvar> <nbclauses>'
- Each clause is a whitespace-separated sequence of non-zero literals terminated by 0.
- Trailing SATLIB metadata markers like '%' are handled cleanly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from core.contracts.models import CNFFormula


def parse_dimacs_cnf(text: str) -> tuple[tuple[tuple[int, ...], ...], int]:
    """Parse DIMACS CNF text into a tuple of clauses and variable count.

    Args:
        text: String containing DIMACS CNF data.

    Returns:
        tuple (clauses, num_vars) where clauses is a tuple of tuples of int literals.

    Raises:
        ValueError: If header is missing/malformed, tokens are invalid, or clause count mismatches.
    """
    lines = text.splitlines()
    header_found = False
    num_vars = 0
    expected_clauses = 0
    clauses: list[tuple[int, ...]] = []
    current_clause: list[int] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("c"):
            continue

        # SATLIB trailing delimiter
        if stripped.startswith("%"):
            break

        if stripped.startswith("p"):
            if header_found:
                raise ValueError("Duplicate problem line 'p cnf' encountered.")
            parts = stripped.split()
            if len(parts) != 4 or parts[1] != "cnf":
                raise ValueError(
                    f"Malformed problem line: {stripped!r}. Expected exactly 4 tokens 'p cnf <nbvar> <nbclauses>'."
                )
            try:
                num_vars = int(parts[2])
                expected_clauses = int(parts[3])
            except ValueError as e:
                raise ValueError(f"Invalid integer in problem line: {stripped!r}") from e
            if num_vars < 0 or expected_clauses < 0:
                raise ValueError(f"Negative numbers in problem line: {stripped!r}")
            header_found = True
            continue

        # If clauses appear before problem line, error
        if not header_found:
            raise ValueError(f"Clause content encountered before 'p cnf' problem line: {stripped!r}")

        # Clause tokens line
        tokens = stripped.split()
        stop_parsing = False
        for token in tokens:
            if token == "%":
                stop_parsing = True
                break
            try:
                lit = int(token)
            except ValueError as e:
                raise ValueError(f"Invalid literal token {token!r} in clause line") from e

            if lit == 0:
                clauses.append(tuple(current_clause))
                current_clause = []
            else:
                current_clause.append(lit)
                abs_lit = abs(lit)
                if abs_lit > num_vars:
                    num_vars = abs_lit

        if stop_parsing:
            break

    if not header_found:
        raise ValueError("Missing problem line 'p cnf <nbvar> <nbclauses>'.")

    if current_clause:
        clauses.append(tuple(current_clause))

    if len(clauses) != expected_clauses:
        raise ValueError(
            f"Clause count mismatch: header declared {expected_clauses} clauses, but parsed {len(clauses)}."
        )

    return tuple(clauses), num_vars


def read_dimacs_file(path: str | Path) -> CNFFormula:
    """Read a DIMACS `.cnf` file from disk and return a `CNFFormula` instance.

    Args:
        path: Path to the .cnf file.

    Returns:
        CNFFormula data model.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"DIMACS file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    clauses, num_vars = parse_dimacs_cnf(content)
    return CNFFormula(
        clauses=clauses,
        num_primary_vars=num_vars,
        num_aux_vars=0,
    )


def to_dimacs_string(
    cnf: CNFFormula,
    comments: Sequence[str] = (),
) -> str:
    """Serialize a `CNFFormula` to standard DIMACS CNF string format.

    Args:
        cnf: The CNFFormula to serialize.
        comments: Optional list of comment strings to prepend.

    Returns:
        Standard DIMACS formatted string.
    """
    lines: list[str] = []
    for comment in comments:
        for c_line in comment.splitlines():
            lines.append(f"c {c_line}")

    lines.append(f"p cnf {cnf.num_vars} {cnf.num_clauses}")

    for clause in cnf.clauses:
        clause_str = " ".join(str(lit) for lit in clause)
        lines.append(f"{clause_str} 0")

    return "\n".join(lines) + "\n"


def write_dimacs_file(
    path: str | Path,
    cnf: CNFFormula,
    comments: Sequence[str] = (),
) -> None:
    """Write a `CNFFormula` to a file in standard DIMACS format.

    Args:
        path: Target file path.
        cnf: The CNFFormula to write.
        comments: Optional comments to write at the beginning.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = to_dimacs_string(cnf, comments)
    target.write_text(text, encoding="utf-8")
