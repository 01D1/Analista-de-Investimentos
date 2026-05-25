"""
src/valuation/models/ — Sector Valuation Models (M016-S02+)

Pacote de modelos de valuation por setor:
  bank_model.py       — M016-S02: Bancos/Financials (COSIF, P/BV justificado, DDM)
  commodity_model.py  — M016-S03: Commodities/Oil & Gas (DCF/FCFF, EV/EBITDA)

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
]
