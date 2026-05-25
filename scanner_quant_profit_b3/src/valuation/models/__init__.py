"""
src/valuation/models/ — Sector Valuation Models (M016-S02+)

Pacote de modelos de valuation por setor:
  bank_model.py       — M016-S02: Bancos/Financials (COSIF, P/BV justificado, DDM)
  commodity_model.py  — M016-S03: Commodities/Oil & Gas (DCF/FCFF, EV/EBITDA)
  utility_model.py    — M016-S04: Utilities (RAB-DCF, DCF/FCFF, EV/EBITDA)
  retail_model.py     — M016-S04: Varejo (DCF/FCFF, EV/EBITDA, DISTRESSED flag)
  industry_model.py   — M016-S04: Indústria + TECH/FALLBACK (DCF/FCFF, EV/EBITDA)

Cada modelo:
  - Declara um dataclass de inputs (SectorValuationInputs)
  - Declara um dataclass de resultado (SectorValuationResult)
  - Implementa hard blocks para dados inválidos
  - Nunca inventa dados / nunca lança exceção por dados ausentes
  - Retorna blocked=True com block_reason descritivo quando inputs insuficientes

Proibido:
  - Calcular sem inputs reais
  - Criar mocks ou dados sintéticos
  - Sobrescrever fair_value existente sem force_recalc=True
"""

from src.valuation.models.bank_model import (
    BankValuationInputs,
    BankValuationResult,
    BankInputQuality,
    BankValuationStatus,
    BankValuationMethod,
    calculate_bank_valuation,
    diagnose_bank_tickers,
)

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
    # Bank model (M016-S02)
    "BankValuationInputs",
    "BankValuationResult",
    "BankInputQuality",
    "BankValuationStatus",
    "BankValuationMethod",
    "calculate_bank_valuation",
    "diagnose_bank_tickers",
    # Commodity model (M016-S03)
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
    # Utility model (M016-S04)
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
    # Retail model (M016-S04)
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
    # Industry model (M016-S04)
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
