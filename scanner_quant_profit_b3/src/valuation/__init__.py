"""
src/valuation/ — Universal Sector Valuation Package

Este pacote é a base para o valuation universal de tickers B3.
Organizado em:
- router.py             — S04: sector router universal
- valuation_results.py  — S05: canonical results store
- valuation_inputs.py   — S05: canonical inputs store
- valuation_coverage.py — S05: canonical coverage store
- valuation_store.py    — S05: unified interface

Veja README.md para documentação completa.
"""

from __future__ import annotations

# Router (S04)
from src.valuation.router import (
    ValuationMethod,
    RoutingStatus,
    Provenance,
    RouterDecision,
    get_valuation_method,
)

# Canonical stores (S05)
from src.valuation.valuation_results import (
    ValuationResult,
    VALUATION_RESULT_COLUMNS,
    load_valuation_result,
    list_valuation_results,
    load_valuation_fair_values,
)

from src.valuation.valuation_inputs import (
    ValuationInputs,
    VALUATION_INPUT_COLUMNS,
    load_valuation_inputs,
    list_valuation_inputs,
)

from src.valuation.valuation_coverage import (
    CoverageStatus,
    ValuationCoverage,
    VALUATION_COVERAGE_COLUMNS,
    load_valuation_coverage,
    load_valuation_coverage_batch,
)

from src.valuation.valuation_store import (
    # unified interface
    load_valuation_result,
    list_valuation_results,
    load_valuation_inputs,
    list_valuation_inputs,
    load_valuation_coverage,
    load_valuation_coverage_batch,
    load_valuation_fair_values,
    save_valuation_result,
    # compatibility shim
    load_latest_valuation_data,
)

__all__ = [
    # Router
    "ValuationMethod",
    "RoutingStatus",
    "Provenance",
    "RouterDecision",
    "get_valuation_method",
    # Types
    "ValuationResult",
    "ValuationInputs",
    "ValuationCoverage",
    "CoverageStatus",
    # Columns
    "VALUATION_RESULT_COLUMNS",
    "VALUATION_INPUT_COLUMNS",
    "VALUATION_COVERAGE_COLUMNS",
    # Results API
    "load_valuation_result",
    "list_valuation_results",
    "load_valuation_fair_values",
    # Inputs API
    "load_valuation_inputs",
    "list_valuation_inputs",
    # Coverage API
    "load_valuation_coverage",
    "load_valuation_coverage_batch",
    # Unified store
    "save_valuation_result",
    "load_latest_valuation_data",
]