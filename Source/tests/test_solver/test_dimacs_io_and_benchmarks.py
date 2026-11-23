"""Tests for DIMACS file I/O and classic benchmark instances (Pigeonhole & 3-SAT)."""

from __future__ import annotations

from pathlib import Path

import pytest
from core.contracts.models import CNFFormula
from solver.dimacs_io import (
    parse_dimacs_cnf,
    read_dimacs_file,
    to_dimacs_string,
    write_dimacs_file,
)
from solver.dpll_solver import DPLLSolver


def make_pigeonhole_cnf(pigeons: int, holes: int) -> CNFFormula:
    """Generate Pigeonhole Principle PHP(pigeons, holes) in CNF.

    Variables: p_{i,j} where 1 <= i <= pigeons and 1 <= j <= holes.
    Index: (i - 1) * holes + j.
    Clauses:
    1. Each pigeon must be in at least one hole: for each i, (p_{i,1} or ... or p_{i,holes})
    2. No two pigeons in same hole: for each j, and distinct i1, i2, (-p_{i1,j} or -p_{i2,j})
    """
    def var(p: int, h: int) -> int:
        return (p - 1) * holes + h

    clauses: list[tuple[int, ...]] = []

    # At least one hole for each pigeon
    for i in range(1, pigeons + 1):
        clauses.append(tuple(var(i, j) for j in range(1, holes + 1)))

    # At most one pigeon per hole
    for j in range(1, holes + 1):
        for i1 in range(1, pigeons + 1):
            for i2 in range(i1 + 1, pigeons + 1):
                clauses.append((-var(i1, j), -var(i2, j)))

    return CNFFormula(
        clauses=tuple(clauses),
        num_primary_vars=pigeons * holes,
    )


def test_dimacs_string_roundtrip() -> None:
    """Test serialization to DIMACS format and parsing back."""
    cnf = CNFFormula(
        clauses=((1, -2), (-1, 2, 3), (-3,)),
        num_primary_vars=3,
    )
    dimacs_text = to_dimacs_string(cnf, comments=["Griductive test"])
    parsed_clauses, num_vars = parse_dimacs_cnf(dimacs_text)

    assert parsed_clauses == cnf.clauses
    assert num_vars == 3


def test_dimacs_file_io(tmp_path: Path) -> None:
    """Test reading and writing DIMACS .cnf files."""
    cnf = CNFFormula(
        clauses=((1, 2), (-1, 3), (-2, -3)),
        num_primary_vars=3,
    )
    file_path = tmp_path / "test_formula.cnf"
    write_dimacs_file(file_path, cnf, comments=["Temporary test CNF"])

    loaded_cnf = read_dimacs_file(file_path)
    assert loaded_cnf.clauses == cnf.clauses
    assert loaded_cnf.num_vars == 3


def test_dimacs_satlib_percent_marker() -> None:
    """Handle SATLIB trailing % and 0 delimiters gracefully."""
    satlib_text = "c SATLIB benchmark\np cnf 2 1\n1 2 0\n%\n0\n"
    clauses, num_vars = parse_dimacs_cnf(satlib_text)
    assert clauses == ((1, 2),)
    assert num_vars == 2


def test_dimacs_missing_header_raises() -> None:
    """Missing problem line 'p cnf' must raise ValueError."""
    with pytest.raises(ValueError, match="Missing problem line"):
        parse_dimacs_cnf("")

    with pytest.raises(ValueError, match="Clause content encountered before"):
        parse_dimacs_cnf("1 2 0\n")


def test_dimacs_clause_count_mismatch_raises() -> None:
    """Header declaring more or fewer clauses than actually present must raise ValueError."""
    text_mismatch = "p cnf 2 3\n1 2 0\n-1 0\n"
    with pytest.raises(ValueError, match="Clause count mismatch"):
        parse_dimacs_cnf(text_mismatch)


def test_dimacs_malformed_problem_line_raises() -> None:
    """Problem line with extra or missing tokens must raise ValueError."""
    with pytest.raises(ValueError, match="Expected exactly 4 tokens"):
        parse_dimacs_cnf("p cnf 2 1 extra\n1 2 0\n")


def test_pigeonhole_unsat_php_3_2() -> None:
    """PHP(3, 2): 3 pigeons in 2 holes must be UNSAT by Dirichlet principle."""
    php32 = make_pigeonhole_cnf(3, 2)
    solver = DPLLSolver()
    result = solver.solve(php32)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks > 0


def test_pigeonhole_unsat_php_4_3() -> None:
    """PHP(4, 3): 4 pigeons in 3 holes must be UNSAT by Dirichlet principle."""
    php43 = make_pigeonhole_cnf(4, 3)
    solver = DPLLSolver()
    result = solver.solve(php43)
    assert result.is_sat is False
    assert result.model is None
    assert result.metrics.backtracks > 0


def test_pigeonhole_sat_php_3_3() -> None:
    """PHP(3, 3): 3 pigeons in 3 holes is SAT (bijection)."""
    php33 = make_pigeonhole_cnf(3, 3)
    solver = DPLLSolver()
    result = solver.solve(php33)
    assert result.is_sat is True
    assert result.model is not None
