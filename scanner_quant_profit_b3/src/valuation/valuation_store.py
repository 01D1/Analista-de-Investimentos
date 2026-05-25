"""
src/valuation/valuation_store.py — Canonical Valuation Store (S05)

Interface unificada para stores canônicos de valuation.
Combina valuation_results.py, valuation_inputs.py e valuation_coverage.py
em um ponto de acesso único, preservando coexistência com valuation_connector.py.

save_valuation_result() — implementação segura (M016-S02):
  - write=False por default (não escreve sem confirmação explícita)
  - force_recalc=False por default (preserva fair_value existente)
  - Registra method_used, input_quality, valuation_date
  - Nunca sobrescreve BBAS3=64.84 ou ITUB4=73.69 sem force_recalc=True
  - Escreve na tabela bank_valuation_results (criada na primeira chamada)

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


# ── Implementação segura de save (M016-S02) ────────────────────────────────────

# Fair values que NÃO podem ser sobrescritos sem force_recalc=True (M016-S02)
_PRESERVED_FAIR_VALUES: dict[str, float] = {
    "BBAS3": 64.84,
    "ITUB4": 73.69,
}


def _ensure_bank_valuation_table(db_path: str) -> None:
    """Cria a tabela bank_valuation_results se não existir."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bank_valuation_results (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at       TEXT    DEFAULT (datetime('now')),
            ticker           TEXT    NOT NULL,
            fair_value       REAL,
            upside_pct       REAL,
            valuation_method TEXT,
            method_used      TEXT,
            confidence       REAL    DEFAULT 0.0,
            input_quality    TEXT,
            valuation_date   TEXT,
            blocked          INTEGER DEFAULT 1,
            block_reason     TEXT,
            status           TEXT,
            notes            TEXT,
            force_recalc     INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_valuation_result(
    ticker: str,
    result: ValuationResult,
    db_path: str | None = None,
    *,
    write: bool = False,
    force_recalc: bool = False,
    method_used: str | None = None,
    input_quality: str | None = None,
    valuation_date: str | None = None,
) -> bool:
    """
    Gravação segura de resultado de valuation (M016-S02).

    CONTRATO DE SEGURANÇA (D077–D082):
    - write=False por default — não escreve sem parâmetro explícito
    - force_recalc=False por default — preserva fair_value existente
    - BBAS3 (64.84) e ITUB4 (73.69) nunca são sobrescritos sem force_recalc=True
    - Registra method_used, input_quality e valuation_date em todos os writes
    - Escreve em bank_valuation_results (tabela separada, não altera asset_intelligence_snapshots)

    Não é chamada automaticamente por nenhum pipeline — somente via chamada explícita.

    Parameters
    ----------
    ticker: str
        Código do ativo B3.
    result: ValuationResult
        Resultado a salvar (não pode ter fair_value=None se write=True).
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.
    write: bool
        Se True, efetua a gravação. Default: False (apenas valida).
    force_recalc: bool
        Se True, permite sobrescrever fair_value existente (incluindo BBAS3/ITUB4).
        Default: False (seguro).
    method_used: str | None
        Método que produziu o resultado (registrado no log de auditoria).
    input_quality: str | None
        Qualidade dos inputs de dados.
    valuation_date: str | None
        Data de referência do valuation (ISO format). Default: hoje.

    Returns
    -------
    bool
        True se o resultado foi gravado com sucesso.
        False se write=False, bloqueado por preserved value, ou erro.
    """
    import logging
    from datetime import date

    log = logging.getLogger(__name__)
    ticker_upper = str(ticker).strip().upper()

    # ── Validação: resultado deve ter fair_value se write=True ──────────────────
    if write and result.fair_value is None:
        log.warning(
            "save_valuation_result: ticker=%s — resultado sem fair_value, write ignorado",
            ticker_upper
        )
        return False

    # ── Proteção BBAS3/ITUB4: não sobrescrever sem force_recalc ────────────────
    if ticker_upper in _PRESERVED_FAIR_VALUES and not force_recalc:
        preserved_fv = _PRESERVED_FAIR_VALUES[ticker_upper]
        log.info(
            "save_valuation_result: ticker=%s — preserved fair_value=%.2f protegido "
            "(force_recalc=False). Use force_recalc=True para sobrescrever.",
            ticker_upper, preserved_fv
        )
        return False

    # ── write=False → apenas validação, sem escrita ─────────────────────────────
    if not write:
        log.debug(
            "save_valuation_result: ticker=%s — write=False, resultado validado mas não gravado",
            ticker_upper
        )
        return False

    # ── Escrita no banco ─────────────────────────────────────────────────────────
    db = db_path or _db_path()
    effective_date = valuation_date or date.today().isoformat()

    try:
        _ensure_bank_valuation_table(db)

        import sqlite3
        conn = sqlite3.connect(db)
        conn.execute(
            """
            INSERT INTO bank_valuation_results
                (ticker, fair_value, upside_pct, valuation_method, method_used,
                 confidence, input_quality, valuation_date, blocked, block_reason,
                 status, notes, force_recalc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker_upper,
                result.fair_value,
                result.upside_pct,
                result.valuation_method,
                method_used or result.valuation_method,
                result.valuation_confidence,
                input_quality or "UNKNOWN",
                effective_date,
                0,  # blocked=False (se chegou aqui é porque fair_value não é None)
                None,
                result.valuation_governance_status,
                None,
                1 if force_recalc else 0,
            ),
        )
        conn.commit()
        conn.close()

        log.info(
            "save_valuation_result: ticker=%s — gravado fair_value=%.2f, method=%s, date=%s",
            ticker_upper, result.fair_value, method_used or result.valuation_method, effective_date
        )
        return True

    except Exception as e:
        log.error("save_valuation_result: ticker=%s — erro ao gravar: %s", ticker_upper, e)
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