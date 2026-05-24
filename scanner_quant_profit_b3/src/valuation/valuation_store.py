"""
src/valuation/valuation_store.py — Canonical Valuation Store (S05)

Interface unificada para stores canônicos de valuation.
Combina valuation_results.py, valuation_inputs.py e valuation_coverage.py
em um ponto de acesso único, preservando coexistência com valuation_connector.py.

Responsável APENAS por leitura. save_valuation_result() existe como stub
seguro para extensões futuras — não é chamado automaticamente.

D077–D082 intocados. D086 (coexistência) respeitado.
Proibido: calcular DCF/COSIF/DDM, criar fair_value, criar dados mockados,
alterar banco manualmente.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd

# Importar stores canônicos
from src.valuation.valuation_results import (
    ValuationResult,
    VALUATION_RESULT_COLUMNS,
    load_valuation_result as _load_result,
    list_valuation_results as _list_results,
    load_valuation_fair_values as _load_fair_values,
)
from src.valuation.valuation_inputs import (
    ValuationInputs,
    VALUATION_INPUT_COLUMNS,
    load_valuation_inputs as _load_inputs,
    list_valuation_inputs as _list_inputs,
)
from src.valuation.valuation_coverage import (
    CoverageStatus,
    ValuationCoverage,
    VALUATION_COVERAGE_COLUMNS,
    load_valuation_coverage as _load_coverage,
    load_valuation_coverage_batch as _load_coverage_batch,
)

# ── Re-exportar tipos públicos ──────────────────────────────────────────────────

__all__ = [
    # Tipos
    "ValuationResult",
    "ValuationInputs",
    "ValuationCoverage",
    "CoverageStatus",
    # Colunas
    "VALUATION_RESULT_COLUMNS",
    "VALUATION_INPUT_COLUMNS",
    "VALUATION_COVERAGE_COLUMNS",
    # Resultados (S05-API-01)
    "load_valuation_result",
    "list_valuation_results",
    # Inputs (S05-API-02)
    "load_valuation_inputs",
    "list_valuation_inputs",
    # Coverage (S05-API-03)
    "load_valuation_coverage",
    "load_valuation_coverage_batch",
    # Fair values (conveniência)
    "load_valuation_fair_values",
    # Stub seguro (S05-API-04) — não usado automaticamente
    "save_valuation_result",
]


# ── Interface unificada (S05-API-01 a S05-API-03) ─────────────────────────────

def load_valuation_result(ticker: str, db_path: str | None = None) -> ValuationResult:
    """
    Carrega resultado de valuation para UM ticker.

    Parameters
    ----------
    ticker: str
        Código do ativo B3 (ex: "PETR4", "BBAS3", "ITUB4", "WEGE3")
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.

    Returns
    -------
    ValuationResult
        Resultado canônico. valuation_available=False → fair_value=None
        (nunca R$ 0,00 falso).
    """
    return _load_result(ticker, db_path)


def list_valuation_results(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Lista resultados de valuation para múltiplos tickers.

    Tickers sem dados aparecem com valuation_available=False e fair_value=None.

    Parameters
    ----------
    tickers: list[str] | None
        Lista de tickers. None = todos disponíveis no banco.
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas VALUATION_RESULT_COLUMNS.
    """
    return _list_results(tickers, db_path)


def load_valuation_inputs(ticker: str, db_path: str | None = None) -> ValuationInputs:
    """
    Carrega inputs para valuation de UM ticker.

    Parameters
    ----------
    ticker: str
        Código do ativo B3.
    db_path: str | None
        Caminho do banco.

    Returns
    -------
    ValuationInputs
        Inputs canônicos com coverage_status inferido.
    """
    return _load_inputs(ticker, db_path)


def list_valuation_inputs(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Lista inputs de valuation para múltiplos tickers.

    Tickers sem dados aparecem com coverage_status='empty'.
    """
    return _list_inputs(tickers, db_path)


def load_valuation_coverage(ticker: str, db_path: str | None = None) -> ValuationCoverage:
    """
    Carrega status de cobertura de valuation para UM ticker.

    Útil para o sector router (S04) decidir bloqueio/procedência.

    Parameters
    ----------
    ticker: str
        Código do ativo B3.
    db_path: str | None
        Caminho do banco.

    Returns
    -------
    ValuationCoverage
        Status de cobertura com contagem de ri_documents.
    """
    return _load_coverage(ticker, db_path)


def load_valuation_coverage_batch(tickers: list[str], db_path: str | None = None) -> pd.DataFrame:
    """
    Lista status de cobertura para múltiplos tickers.

    Tickers sem dados são incluídos com coverage_status='empty'.
    """
    return _load_coverage_batch(tickers, db_path)


# ── Fair values (conveniência) ─────────────────────────────────────────────────

def load_valuation_fair_values(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Retorna DataFrame mínimo com ticker, fair_value, upside_pct.
    Omite tickers sem fair_value válido. Para detectar ausência,
    use list_valuation_results().
    """
    return _load_fair_values(tickers, db_path)


# ── Stub seguro (S05-API-04) ────────────────────────────────────────────────────

def save_valuation_result(ticker: str, result: ValuationResult, db_path: str | None = None) -> bool:
    """
    Stub SEGURO para gravação futura de resultados de valuation.

    ATENÇÃO: Esta função existe apenas como interface.
    Não é chamada automaticamente por nenhum componente.
    Qualquer implementação real deve:
    - Validar D077–D082 (governança de valuation)
    - Passar por revisão antes de ativar
    - Ser integrada ao pipeline de forma controlada

    Current status: NOT IMPLEMENTED (stub only).

    Parameters
    ----------
    ticker: str
        Código do ativo.
    result: ValuationResult
        Resultado a salvar.
    db_path: str | None
        Caminho do banco.

    Returns
    -------
    bool
        Sempre False (stub).
    """
    # Stub — não executar. Implementar com D077–D082 compliance quando pronto.
    return False


# ── Compatibilidade com valuation_connector.py (M012/M013) ────────────────────

def load_latest_valuation_data(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Compatibility shim para valuation_connector.py.

    Converte output do store canônico no formato esperado por
    valuation_connector.py (colunas VALUATION_COLUMNS).
    Usado apenas onde valuation_connector é consumido.

    Nota: Esta função é uma camada de adaptação, não uma duplicação.
    O store canônico (S05) é a fonte primária; esta shim garante
    compatibilidade reversa com M012/M013.
    """
    if not tickers:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)

    df = list_valuation_results(tickers, db_path)
    if df.empty:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)

    # Mapear para formato do connector
    out = df.rename(
        columns={
            "trade_date": "trade_date",
            "data_valuation": "trade_date",
        }
    )
    # Garantir que todas as colunas do connector existam
    connector_cols = [
        "ticker", "valuation_available", "fair_value", "upside_pct",
        "valuation_method", "valuation_confidence",
        "fundamental_quality_score", "financial_health_score",
        "profitability_score", "growth_score", "leverage_score",
        "valuation_governance_status",
    ]
    for col in connector_cols:
        if col not in out.columns:
            out[col] = pd.NA
    return out[connector_cols]