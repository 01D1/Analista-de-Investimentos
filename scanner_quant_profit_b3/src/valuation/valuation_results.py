"""
src/valuation/valuation_results.py — Canonical Valuation Results Store (S05)

Armazena resultados canônicos de valuation: preço-alvo, upside, método,
confiança e scores setoriais. Apenas leitura — nunca calcula, nunca cria
mock, nunca altera banco.

Fontes de dados (por precedência):
  1. asset_intelligence_snapshots (banco SQLite) — fonte primária
  2. outputs/Valuation_TICKER_*.xlsx (pipeline legacy) — fallback

Esse arquivo coexiste com valuation_connector.py (M012/M013).
NÃO substitui, NÃO duplica, NÃO recalcula.

D077–D082 intocados. D086 (coexistência) respeitado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table

# ── Colunas canônicas ──────────────────────────────────────────────────────────

VALUATION_RESULT_COLUMNS = [
    "ticker",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "valuation_available",
    "valuation_governance_status",
    "trade_date",
    "data_valuation",
    "fonte",
]

_VALUATION_RESULT_RAW_COLS = [
    "ticker",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "valuation_available",
    "valuation_governance_status",
    "trade_date",
]


# ── Sentinel para "sem valuation" ──────────────────────────────────────────────

@dataclass
class ValuationResult:
    """Representa um resultado de valuation para um ticker.

    Usar este dataclass para retornos tipados. Quando não há valuation,
    fair_value=None, valuation_available=False.
    Nunca retornar 0.0 para fair_value quando não há dados.
    """

    ticker: str
    fair_value: Optional[float] = None
    upside_pct: Optional[float] = None
    valuation_method: Optional[str] = None
    valuation_confidence: float = 0.0
    valuation_available: bool = False
    valuation_governance_status: str = "VALUATION_MISSING"
    trade_date: Optional[str] = None
    data_valuation: Optional[str] = None
    fonte: Optional[str] = None

    @classmethod
    def empty(cls, ticker: str) -> "ValuationResult":
        """Factory para ticker sem valuation — nunca 0.0 falso."""
        return cls(
            ticker=ticker,
            fair_value=None,
            upside_pct=None,
            valuation_method=None,
            valuation_confidence=0.0,
            valuation_available=False,
            valuation_governance_status="VALUATION_MISSING",
        )

    @classmethod
    def from_row(cls, row: dict) -> "ValuationResult":
        """Constrói a partir de uma linha de DataFrame."""
        return cls(
            ticker=str(row.get("ticker", "")).strip().upper(),
            fair_value=float(row["fair_value"]) if pd.notna(row.get("fair_value")) else None,
            upside_pct=float(row["upside_pct"]) if pd.notna(row.get("upside_pct")) else None,
            valuation_method=str(row["valuation_method"]) if pd.notna(row.get("valuation_method")) else None,
            valuation_confidence=float(row["valuation_confidence"]) if pd.notna(row.get("valuation_confidence")) else 0.0,
            valuation_available=bool(row["valuation_available"]) if pd.notna(row.get("valuation_available")) else False,
            valuation_governance_status=str(row.get("valuation_governance_status", "VALUATION_MISSING")),
            trade_date=str(row["trade_date"]) if pd.notna(row.get("trade_date")) else None,
            data_valuation=str(row.get("data_valuation", "")),
            fonte=str(row.get("fonte", "")),
        )


# ── Leitura do banco ────────────────────────────────────────────────────────────

def _db_path() -> str:
    """Caminho do banco de dados principal. Localizável via variável ou fallback."""
    import os, sqlite3
    db_env = os.environ.get("SCANNER_QUANT_DB")
    if db_env and sqlite3.complete_statement(db_env):
        return db_env
    return "scanner_quant.db"


def _load_from_asset_intelligence(db_path: str, tickers: list[str] | None = None) -> pd.DataFrame:
    """Lê fair_value/upside/método de asset_intelligence_snapshots."""
    rows = read_table(db_path, "asset_intelligence_snapshots", _VALUATION_RESULT_RAW_COLS + ["trade_date"], order_by="id DESC", limit=5000)
    if rows.empty:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)
    rows = filter_tickers(rows, tickers)
    if not rows.empty:
        rows = rows.sort_values(["ticker", "trade_date"], ascending=[True, False]).groupby("ticker", as_index=False).first()
    for col in VALUATION_RESULT_COLUMNS:
        if col not in rows.columns:
            rows[col] = pd.NA
    rows["data_valuation"] = rows["trade_date"]  # trade_date funciona como data de referência
    rows["fonte"] = "asset_intelligence_snapshots"
    return rows[VALUATION_RESULT_COLUMNS]


# ── Fallback via valuation_bridge (S05-DB-01) ──────────────────────────────────

def _load_from_outputs(db_path: str, tickers: list[str] | None) -> pd.DataFrame:
    """Fallback: tenta outputs/Valuation_TICKER_*.xlsx via valuation_bridge."""
    from pathlib import Path
    from src.integration.valuation_bridge import get_valuations_batch

    outputs_dir = Path("..") / "12_PYTHON" / "pipeline banco completo" / "outputs"
    if not outputs_dir.exists():
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)

    ticker_list = tickers or []
    if not ticker_list:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)

    valuations = get_valuations_batch(ticker_list, outputs_dir)
    rows = []
    for ticker in ticker_list:
        val = valuations.get(ticker) or {}
        if not val:
            continue
        rows.append({
            "ticker": ticker,
            "fair_value": val.get("preco_alvo"),
            "upside_pct": val.get("upside_pct"),
            "valuation_method": val.get("valuation_method", "DCF/planilha"),
            "valuation_confidence": 0.6,
            "valuation_available": True,
            "valuation_governance_status": "VALUATION_AVAILABLE",
            "trade_date": val.get("data_valuation"),
            "data_valuation": val.get("data_valuation"),
            "fonte": val.get("fonte", "outputs/excel"),
        })
    if not rows:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)
    return pd.DataFrame(rows)[VALUATION_RESULT_COLUMNS]


# ── Interface pública ──────────────────────────────────────────────────────────

def load_valuation_result(ticker: str, db_path: str | None = None) -> ValuationResult:
    """
    Carrega resultado de valuation para UM ticker.

    Retorna ValuationResult com valuation_available=False quando não há dados.
    fair_value=None (não 0.0) para tickers sem valuation — evita R$ 0,00 falso.

    Parameters
    ----------
    ticker: str
        Código do ativo B3 (ex: "PETR4", "BBAS3")
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.

    Returns
    -------
    ValuationResult
        Resultado canônico para o ticker.
    """
    db = db_path or _db_path()
    ticker_upper = str(ticker).strip().upper()

    # Tenta fonte primária (banco)
    df_db = _load_from_asset_intelligence(db, [ticker_upper])
    if not df_db.empty:
        return ValuationResult.from_row(df_db.iloc[0].to_dict())

    # Fallback outputs
    df_out = _load_from_outputs(db, [ticker_upper])
    if not df_out.empty:
        return ValuationResult.from_row(df_out.iloc[0].to_dict())

    # Sem dados → sentinel EMPTY, não 0.0
    return ValuationResult.empty(ticker_upper)


def list_valuation_results(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Lista resultados de valuation para múltiplos tickers.

    Tickers sem dados são incluídos com valuation_available=False e
    fair_value=None (não linhas omitidas).

    Parameters
    ----------
    tickers: list[str] | None
        Lista de tickers. None = todos os disponíveis no banco.
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas VALUATION_RESULT_COLUMNS. Pode estar vazio
        (não None) quando nenhum ticker tem valuation.
    """
    db = db_path or _db_path()
    df = _load_from_asset_intelligence(db, tickers)

    # Se fonte primária não retornou tickers, tenta fallback em tudo
    if df.empty and tickers:
        df = _load_from_outputs(db, tickers)

    # Se ainda vazio, retorna DataFrame vazio (não preenche com 0.0)
    if df.empty:
        return pd.DataFrame(columns=VALUATION_RESULT_COLUMNS)

    return df.reset_index(drop=True)


def load_valuation_fair_values(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Retorna DataFrame mínimo com ticker, fair_value, upside_pct.
    Tickers sem dados são omitidos — use list_valuation_results para
    detectar ausência.
    """
    df = list_valuation_results(tickers, db_path)
    if df.empty:
        return pd.DataFrame(columns=["ticker", "fair_value", "upside_pct"])
    out = df[["ticker", "fair_value", "upside_pct"]].copy()
    # Omitir tickers sem fair_value válido
    out = out[out["fair_value"].notna()]
    return out.reset_index(drop=True)


__all__ = [
    "ValuationResult",
    "VALUATION_RESULT_COLUMNS",
    "load_valuation_result",
    "list_valuation_results",
    "load_valuation_fair_values",
]