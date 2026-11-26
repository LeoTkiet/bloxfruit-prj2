"""Logic representation, region resolution, and CNF encoding package (owned by TV2).

Public API:
    CNFEncoder                 - implements ICNFEncoder (also exported at package root
                                 so TV4's encoder_factory can discover it)
    DirectSemanticEvaluator    - implements IDirectEvaluator (ground-truth oracle)
    VariableMapper             - deterministic cell <-> variable mapping
    AuxVarAllocator            - auxiliary variable allocator
    resolve_region_cells       - deterministic RegionSpec resolver
"""

from __future__ import annotations

from logic.cnf_encoder import CNFEncoder
from logic.evaluator import (
    DirectSemanticEvaluator,
    evaluate_cnf_clauses,
    evaluate_formula,
)
from logic.region_resolver import RegionResolutionError, resolve_region_cells
from logic.variable_mapper import (
    AuxVarAllocator,
    VariableMapper,
    cell_to_var,
    var_to_cell,
)

__all__ = [
    "CNFEncoder",
    "DirectSemanticEvaluator",
    "RegionResolutionError",
    "VariableMapper",
    "AuxVarAllocator",
    "resolve_region_cells",
    "cell_to_var",
    "var_to_cell",
    "evaluate_cnf_clauses",
    "evaluate_formula",
]
