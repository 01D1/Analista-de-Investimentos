"""
src/valuation/models/ — Sector Valuation Models (M016-S02+)

Pacote de modelos de valuation por setor:
  bank_model.py   — M016-S02: Bancos/Financials (COSIF, P/BV justificado, DDM)

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

__all__ = [
    "BankValuationInputs",
    "BankValuationResult",
    "BankInputQuality",
    "BankValuationStatus",
    "BankValuationMethod",
    "calculate_bank_valuation",
    "diagnose_bank_tickers",
]
