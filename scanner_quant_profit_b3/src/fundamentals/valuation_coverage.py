"""
src/fundamentals/valuation_coverage.py

Cobertura operacional de valuation por ticker.
Classifica cada ativo da watchlist segundo o estado real dos dados
fundamentalistas, sem criar mocks, sem calcular valuation, sem alterar dados.

Baseado em: docs/coverage_audit_20260523.csv (M014-S01 audit)
"""

from __future__ import annotations

import enum
import sqlite3
from pathlib import Path
from typing import Iterator

# ──────────────────────────────────────────────
#  Paths
# ──────────────────────────────────────────────

_DB_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "scanner_quant.db"
    if (Path(__file__).resolve().parents[2] / "data" / "scanner_quant.db").exists()
    else Path(__file__).resolve().parents[2] / "data" / "scanner_quant.db"
)

_AUDIT_CSV = (
    Path(__file__).resolve().parents[1].parent / "docs" / "coverage_audit_20260523.csv"
)


# ──────────────────────────────────────────────
#  Enum — CoverageStatus
# ──────────────────────────────────────────────

class CoverageStatus(enum.Enum):
    """
    Status de cobertura por ticker.

    READY          — tem AI entry + CVM docs + valuation flag + fair_value + market_price
    PARTIAL        — tem AI entry + CVM docs, mas faltan campos-chave (method/fqs/sector)
    EMPTY          — não tem AI entry (nenhum dado de valuation disponível)
    NEEDS_MODEL    — tem AI entry + CVM docs + fair_value, mas falta valuation_method ou FQS
    NEEDS_DATA     — tem AI entry, mas falta CVM docs OU valuation flag=0 OU gap crítico
    """
    READY = "ready"          # completo para rodar modelo
    PARTIAL = "partial"      # dados basicos ok, faltan metadados
    EMPTY = "empty"          # sem AI entry
    NEEDS_MODEL = "needs_model"   # dados OK, falta o modelo
    NEEDS_DATA = "needs_data"     # dados basilares faltam


# ──────────────────────────────────────────────
#  Classificação por ticker (base audit S01)
# ──────────────────────────────────────────────
#
# Regras baseadas nos dados reais do CSV de auditoria:
#
# Campo              | 0/9   | 5/9  | 7/9   | 4/9  | 0/9 | 0/9 | 0/9 | 0/9
# --------------------+-------+------+-------+------+-----+-----+-----+----
# AI present         | 7/9   | bpac11, sanb11 = False
# cvm_docs_count     | 5/9   | BPAC11=0, SANB11=0, SUZB3=0, VALE3=0
# valuation_available| 7/9   | bpac11, sanb11 = NULL (sem AI)
# fair_value         | 4/9   | BBAS3=64.84, ITUB4=73.69, PETR4=81.12, WEGE3=40.16
# valuation_method   | 0/9   | null em todos
# fundamental_quality_score | 0/9 | null em todos
# sector             | 0/9   | null em todos
# company_name       | 0/9   | null em todos
# ai_market_price    | 0/9   | null em todos
# cvm_trace_discrepancy | True | BPAC11=True, SANB11=True, SUZB3=True
#
# Para BPAC11, SANB11, SUZB3: discrepancy=True (trace=6100, ri_docs=0)
# → falha de pipeline: coleta registrada mas dados nao inseridos.
#
# VALE3: trace=0, ri_docs=0, valuation_flag=0, ai_present=True, cvm_trace_discrepancy=False
# → pipeline nunca executou para VALE3; AI entry existe mas dadosBasicos faltam.
#
# BBAS3, BBDC4, ITUB4, PETR4, WEGE3: ai_present=True, cvm_docs>0, sem discrepancy
# → PARTIAL (metadados faltam mas dados basicos existem)
#
# BBDC4: valuation_available=1, mas fair_value=NULL
# → NEEDS_MODEL (tem flag mas nao tem valor calculado)
#
# Regras finais de classificacao:
#
#  EMPTY       : ai_present=False  (BPAC11, SANB11)
#  NEEDS_DATA  : ai_present=True AND (cvm_docs_count=0 OR valuation_available=0)
#                E cvm_trace_discrepancy=True  → NEEDS_DATA (BPAC11, SANB11 via discrepancy)
#                E cvm_trace_discrepancy=False → NEEDS_DATA (SUZB3, VALE3)
#  PARTIAL     : ai_present=True, cvm_docs>0, valuation_available=1, fair_value=NULL
#                E (valuation_method=NULL OR fundamental_quality_score=NULL)
#  NEEDS_MODEL : ai_present=True, cvm_docs>0, valuation_available=1,
#                fair_value!=NULL E (valuation_method=NULL OR fqs=NULL)
#  READY       : NENHUM ticker qualifies para READY (0% em method e fqs)

_TICKER_CLASSIFICATION: dict[str, CoverageStatus] = {
    # EMPTY — sem AI entry
    "BPAC11": CoverageStatus.NEEDS_DATA,   # ai=False, discrepancy=True
    "SANB11": CoverageStatus.NEEDS_DATA,    # ai=False, discrepancy=True
    # NEEDS_DATA — AI existe mas dados basicos faltam
    "SUZB3":  CoverageStatus.NEEDS_DATA,    # ai=True, cvm=0, discrepancy=True, flag=0
    "VALE3":  CoverageStatus.NEEDS_DATA,    # ai=True, cvm=0, trace=0, flag=0 — pior caso
    # PARTIAL — AI + CVM OK, faltam metadados e fair_value
    "BBDC4":  CoverageStatus.NEEDS_MODEL,   # ai=True, cvm=125, flag=1, fair_value=NULL
    # PARTIAL — AI + CVM OK, fair_value existe, faltan method/fqs/sector
    "BBAS3":  CoverageStatus.PARTIAL,      # ai=True, cvm=121, fair_value=64.84, method=NULL, fqs=NULL
    "ITUB4":  CoverageStatus.PARTIAL,      # ai=True, cvm=125, fair_value=73.69, method=NULL, fqs=NULL
    "PETR4":  CoverageStatus.PARTIAL,      # ai=True, cvm=131, fair_value=81.12, method=NULL, fqs=NULL
    "WEGE3":  CoverageStatus.PARTIAL,      # ai=True, cvm=124, fair_value=40.16, method=NULL, fqs=NULL
}


# ──────────────────────────────────────────────
#  classify_coverage(ticker) — ponto de entrada
# ──────────────────────────────────────────────

def classify_coverage(ticker: str) -> CoverageStatus:
    """
    Retorna o CoverageStatus de um ticker.

    Usa classificacao pre-computada do audit S01.
    Para tickers fora da watchlist, retorna CoverageStatus.EMPTY.
    """
    return _TICKER_CLASSIFICATION.get(str(ticker).upper(), CoverageStatus.EMPTY)


# ──────────────────────────────────────────────
#  CoverageMatrix
# ──────────────────────────────────────────────

class CoverageMatrix:
    """
    Matriz de cobertura operacional de valuation.

    Use para:
    - listar tickers por status
    - saber quais precisam de coleta (NEEDS_DATA)
    - saber quais estao prontos para modelo (READY/NDS_MODEL)
    - gerar diagnostico resumido
    """

    WATCHLIST: list[str] = [
        "BBAS3", "BBDC4", "BPAC11", "ITUB4", "PETR4",
        "SANB11", "SUZB3", "VALE3", "WEGE3",
    ]

    def __init__(self) -> None:
        self._cache: dict[str, CoverageStatus] = {
            t: classify_coverage(t) for t in self.WATCHLIST
        }

    # ── consultas por status ──

    def get_tickers_by_status(self, status: CoverageStatus) -> list[str]:
        """Retorna tickers com um dado status."""
        return [t for t, s in self._cache.items() if s == status]

    def tickers_need_data(self) -> list[str]:
        """Tickers que precisam de ingestao de dados (CVM/historico)."""
        return self.get_tickers_by_status(CoverageStatus.NEEDS_DATA)

    def tickers_ready_for_model(self) -> list[str]:
        """Tickers que tem dados basicos e podem receber um modelo."""
        return self.get_tickers_by_status(CoverageStatus.PARTIAL) + \
               self.get_tickers_by_status(CoverageStatus.NEEDS_MODEL)

    def tickers_need_model(self) -> list[str]:
        """Tickers que tem tudo exceto valuation_method e/ou FQS."""
        return self.get_tickers_by_status(CoverageStatus.NEEDS_MODEL)

    def summary_counts(self) -> dict[str, int]:
        """
        Contagem de tickers por status.
        Inclui 'unknown' para tickers fora da watchlist.
        """
        counts: dict[str, int] = {s.value: 0 for s in CoverageStatus}
        counts["unknown"] = 0
        for s in self._cache.values():
            counts[s.value] += 1
        return counts

    # ── iteraçao ──

    def __iter__(self) -> Iterator[tuple[str, CoverageStatus]]:
        """Iterar sobre (ticker, status) na watchlist."""
        return iter(self._cache.items())

    def items(self) -> list[tuple[str, CoverageStatus]]:
        """Lista de (ticker, status) ordenados por status."""
        return sorted(
            self._cache.items(),
            key=lambda x: (x[1].value, x[0]),
        )

    # ── diagnostico completo ──

    def diagnose(self) -> dict:
        """
        Retorna dicionario com diagnostico operacional.

        Estrutura:
        {
            "summary": dict[str, int],
            "by_status": dict[str, list[str]],
            "needs_data": [...],
            "needs_model": [...],
            "ready": [...],
            "partial": [...],
            "empty": [...],
            "gaps_summary": dict[str, int],
        }
        """
        by_status: dict[str, list[str]] = {}
        for s in CoverageStatus:
            by_status[s.value] = self.get_tickers_by_status(s)

        # gaps mapeados do audit S01
        gaps_summary = {
            "ai_entry_missing": len(by_status["needs_data"]),
            "cvm_docs_missing": 4,   # BPAC11, SANB11, SUZB3, VALE3
            "valuation_method_missing": 9,   # 0/9 tem — TODO: calcular dinamicamente
            "fqs_missing": 9,
            "sector_missing": 9,
            "fair_value_missing": 2,  # BBDC4, SUZB3, VALE3 (flag=0)
            "discrepancy_cvm": 3,     # BPAC11, SANB11, SUZB3
            "ai_market_price_missing": 9,
        }

        return {
            "summary": self.summary_counts(),
            "by_status": by_status,
            "needs_data": self.tickers_need_data(),
            "needs_model": self.tickers_need_model(),
            "ready": self.get_tickers_by_status(CoverageStatus.READY),
            "partial": self.get_tickers_by_status(CoverageStatus.PARTIAL),
            "empty": self.get_tickers_by_status(CoverageStatus.EMPTY),
            "gaps_summary": gaps_summary,
        }

    # ── acesso direto por ticker ──

    def status(self, ticker: str) -> CoverageStatus:
        """Retorna status de um ticker especifico."""
        return self._cache.get(ticker.upper(), CoverageStatus.EMPTY)


# ──────────────────────────────────────────────
#  Exports
# ──────────────────────────────────────────────

__all__ = [
    "CoverageStatus",
    "CoverageMatrix",
    "classify_coverage",
]