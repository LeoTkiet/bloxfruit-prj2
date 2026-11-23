"""DPLL SAT Solver package (owned by TV3).

Exports:
- `DPLLSolver`: pure Python SAT solver implementing `ISATSolver`.
- `DPLLConfig`: configuration options for heuristics and optimizations.
- `parse_dimacs_cnf`, `read_dimacs_file`, `to_dimacs_string`, `write_dimacs_file`:
  DIMACS file format I/O utilities.
- Heuristics: `lexicographic_heuristic`, `moms_heuristic`, `jw_heuristic`, `find_pure_literals`.
"""

from __future__ import annotations

from solver.dimacs_io import (
    parse_dimacs_cnf,
    read_dimacs_file,
    to_dimacs_string,
    write_dimacs_file,
)
from solver.dpll_solver import DPLLSolver
from solver.heuristics import (
    DPLLConfig,
    find_pure_literals,
    jw_heuristic,
    lexicographic_heuristic,
    moms_heuristic,
    select_branching_variable,
)

__all__ = [
    "DPLLSolver",
    "DPLLConfig",
    "parse_dimacs_cnf",
    "read_dimacs_file",
    "to_dimacs_string",
    "write_dimacs_file",
    "select_branching_variable",
    "lexicographic_heuristic",
    "moms_heuristic",
    "jw_heuristic",
    "find_pure_literals",
]
