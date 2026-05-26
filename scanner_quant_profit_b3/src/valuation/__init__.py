"""
src/valuation/ — Universal Sector Valuation Package

Este pacote é a base para o valuation universal de tickers B3.
Organizado em:
- sector_normalizer.py  — M016-S01: sector normalization (GICS/type → canonical key)
- tickers_config.py     — M016-S01: tickers.yaml config loader
- router.py             — S04: sector router universal
- valuation_results.py  — S05: canonical results store
- valuation_inputs.py   — S05: canonical inputs store
- valuation_coverage.py — S05: canonical coverage store
- valuation_store.py    — S05: unified interface (save seguro: M016-S02)
- models/bank_model.py  — M016-S02: Bank Valuation Model

Veja README.md para documentação completa.
"""

from __future__ import annotations

# SectorNormalizer (M016-S01)
from src.valuation.sector_normalizer import (
    SectorNormalizationResult,
    SectorNormalizer,
    NormalizationSource,
    CANONICAL_KEYS,
    FALLBACK_CANONICAL,
    TYPE_TO_CANONICAL,
    GICS_SECTOR_TO_CANONICAL,
    normalize_sector,
    get_normalizer,
)

# Tickers config loader (M016-S01)
from src.valuation.tickers_config import (
    load_tickers_config,
    get_ticker_config,
    get_ticker_type,
)

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

# Bank Valuation Model (M016-S02)
from src.valuation.models.bank_model import (
    BankValuationInputs,
    BankValuationResult,
    BankInputQuality,
    BankValuationStatus,
    BankValuationMethod,
    BANK_TICKERS,
    PRESERVED_FAIR_VALUES,
    calculate_bank_valuation,
    diagnose_bank_tickers,
)

# Commodity Valuation Model (M016-S03)
from src.valuation.models.commodity_model import (
    CommodityValuationInputs,
    CommodityValuationResult,
    CommodityInputQuality,
    CommodityValuationStatus,
    CommodityValuationMethod,
    COMMODITY_TICKERS,
    OIL_GAS_TICKERS,
    MINING_TICKERS,
    COMMODITY_PRESERVED_FAIR_VALUES,
    calculate_commodity_valuation,
    diagnose_commodity_tickers,
    save_commodity_valuation_result,
)

# Utility Valuation Model (M016-S04)
from src.valuation.models.utility_model import (
    UtilityValuationInputs,
    UtilityValuationResult,
    UtilityInputQuality,
    UtilityValuationStatus,
    UtilityValuationMethod,
    UTILITY_TICKERS,
    UTILITY_PRESERVED_FAIR_VALUES,
    DEFAULT_UTILITY_EV_EBITDA_MULTIPLE,
    calculate_utility_valuation,
    diagnose_utility_tickers,
    save_utility_valuation_result,
)

# Retail Valuation Model (M016-S04)
from src.valuation.models.retail_model import (
    RetailValuationInputs,
    RetailValuationResult,
    RetailInputQuality,
    RetailValuationStatus,
    RetailValuationMethod,
    RETAIL_TICKERS,
    RETAIL_PRESERVED_FAIR_VALUES,
    DEFAULT_RETAIL_EV_EBITDA_MULTIPLE,
    calculate_retail_valuation,
    diagnose_retail_tickers,
    save_retail_valuation_result,
)

# Financial Inputs Bridge (M017-S05)
from src.valuation.financial_inputs_bridge import (
    load_financial_inputs_from_store,
    build_commodity_inputs_from_store,
    build_utility_inputs_from_store,
    build_retail_inputs_from_store,
    build_industry_inputs_from_store,
    run_dry_run_all,
    TICKER_SECTOR_MAP,
    TICKER_SUBSECTOR_MAP,
    WACC_DEFAULTS,
    M017_DRY_RUN_TICKERS,
)

# Industry Valuation Model (M016-S04)
from src.valuation.models.industry_model import (
    IndustryValuationInputs,
    IndustryValuationResult,
    IndustryInputQuality,
    IndustryValuationStatus,
    IndustryValuationMethod,
    INDUSTRY_TICKERS,
    TECH_FALLBACK_TICKERS,
    ALL_INDUSTRY_TICKERS,
    INDUSTRY_PRESERVED_FAIR_VALUES,
    DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE,
    calculate_industry_valuation,
    diagnose_industry_tickers,
    save_industry_valuation_result,
)

__all__ = [
    # SectorNormalizer (M016-S01)
    "SectorNormalizationResult",
    "SectorNormalizer",
    "NormalizationSource",
    "CANONICAL_KEYS",
    "FALLBACK_CANONICAL",
    "TYPE_TO_CANONICAL",
    "GICS_SECTOR_TO_CANONICAL",
    "normalize_sector",
    "get_normalizer",
    # Tickers config (M016-S01)
    "load_tickers_config",
    "get_ticker_config",
    "get_ticker_type",
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
    # Bank Valuation Model (M016-S02)
    "BankValuationInputs",
    "BankValuationResult",
    "BankInputQuality",
    "BankValuationStatus",
    "BankValuationMethod",
    "BANK_TICKERS",
    "PRESERVED_FAIR_VALUES",
    "calculate_bank_valuation",
    "diagnose_bank_tickers",
    # Commodity Valuation Model (M016-S03)
    "CommodityValuationInputs",
    "CommodityValuationResult",
    "CommodityInputQuality",
    "CommodityValuationStatus",
    "CommodityValuationMethod",
    "COMMODITY_TICKERS",
    "OIL_GAS_TICKERS",
    "MINING_TICKERS",
    "COMMODITY_PRESERVED_FAIR_VALUES",
    "calculate_commodity_valuation",
    "diagnose_commodity_tickers",
    "save_commodity_valuation_result",
    # Utility Valuation Model (M016-S04)
    "UtilityValuationInputs",
    "UtilityValuationResult",
    "UtilityInputQuality",
    "UtilityValuationStatus",
    "UtilityValuationMethod",
    "UTILITY_TICKERS",
    "UTILITY_PRESERVED_FAIR_VALUES",
    "DEFAULT_UTILITY_EV_EBITDA_MULTIPLE",
    "calculate_utility_valuation",
    "diagnose_utility_tickers",
    "save_utility_valuation_result",
    # Retail Valuation Model (M016-S04)
    "RetailValuationInputs",
    "RetailValuationResult",
    "RetailInputQuality",
    "RetailValuationStatus",
    "RetailValuationMethod",
    "RETAIL_TICKERS",
    "RETAIL_PRESERVED_FAIR_VALUES",
    "DEFAULT_RETAIL_EV_EBITDA_MULTIPLE",
    "calculate_retail_valuation",
    "diagnose_retail_tickers",
    "save_retail_valuation_result",
    # Financial Inputs Bridge (M017-S05)
    "load_financial_inputs_from_store",
    "build_commodity_inputs_from_store",
    "build_utility_inputs_from_store",
    "build_retail_inputs_from_store",
    "build_industry_inputs_from_store",
    "run_dry_run_all",
    "TICKER_SECTOR_MAP",
    "TICKER_SUBSECTOR_MAP",
    "WACC_DEFAULTS",
    "M017_DRY_RUN_TICKERS",
    # Industry Valuation Model (M016-S04)
    "IndustryValuationInputs",
    "IndustryValuationResult",
    "IndustryInputQuality",
    "IndustryValuationStatus",
    "IndustryValuationMethod",
    "INDUSTRY_TICKERS",
    "TECH_FALLBACK_TICKERS",
    "ALL_INDUSTRY_TICKERS",
    "INDUSTRY_PRESERVED_FAIR_VALUES",
    "DEFAULT_INDUSTRY_EV_EBITDA_MULTIPLE",
    "calculate_industry_valuation",
    "diagnose_industry_tickers",
    "save_industry_valuation_result",
]