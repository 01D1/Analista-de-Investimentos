"""
src/valuation/valuation_inputs.py — Canonical Valuation Inputs Store (S05)

Armazena inputs de valuation: setor, subsector, coverage status, scores
fundamentais. Apenas leitura — nunca calcula, nunca cria mock, nunca altera banco.

Fontes de dados:
  1. asset_intelligence_snapshots (banco SQLite) — setor, subsector, scores
  2. b3_financials/ (CSV/XLSX) — dados fundamentalistas

Esse arquivo coexiste com valuation_connector.py (M012/M013).
D077–D082 intocados. D086 (coexistência) respeitado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table

# ── Colunas canônicas ──────────────────────────────────────────────────────────

VALUATION_INPUT_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "subsector",
    "market_price",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "trade_date",
    "fonte",
    "coverage_status",
]

_VALUATION_INPUT_RAW_COLS = [
    "ticker",
    "company_name",
    "sector",
    "subsector",
    "market_price",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "trade_date",
]


# ── Sentinel ────────────────────────────────────────────────────────────────────────

@dataclass
class ValuationInputs:
    """Inputs canônicos para valuation de um ticker.

    Usar este dataclass para retornos tipados. Quando não há dados,
    coverage_status='empty' e scores=None. Nunca retornar 0.0 falso.
    """

    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    subsector: Optional[str] = None
    market_price: Optional[float] = None
    fundamental_quality_score: Optional[float] = None
    financial_health_score: Optional[float] = None
    profitability_score: Optional[float] = None
    growth_score: Optional[float] = None
    leverage_score: Optional[float] = None
    trade_date: Optional[str] = None
    fonte: str = "asset_intelligence_snapshots"
    coverage_status: str = "empty"

    @classmethod
    def empty(cls, ticker: str) -> "ValuationInputs":
        """Factory para ticker sem inputs — coverage_status='empty'."""
        return cls(ticker=ticker, coverage_status="empty")

    @classmethod
    def from_row(cls, row: dict) -> "ValuationInputs":
        """Constrói a partir de uma linha de DataFrame."""
        return cls(
            ticker=str(row.get("ticker", "")).strip().upper(),
            company_name=str(row["company_name"]) if pd.notna(row.get("company_name")) else None,
            sector=str(row["sector"]) if pd.notna(row.get("sector")) else None,
            subsector=str(row["subsector"]) if pd.notna(row.get("subsector")) else None,
            market_price=float(row["market_price"]) if pd.notna(row.get("market_price")) else None,
            fundamental_quality_score=float(row["fundamental_quality_score"]) if pd.notna(row.get("fundamental_quality_score")) else None,
            financial_health_score=float(row["financial_health_score"]) if pd.notna(row.get("financial_health_score")) else None,
            profitability_score=float(row["profitability_score"]) if pd.notna(row.get("profitability_score")) else None,
            growth_score=float(row["growth_score"]) if pd.notna(row.get("growth_score")) else None,
            leverage_score=float(row["leverage_score"]) if pd.notna(row.get("leverage_score")) else None,
            trade_date=str(row["trade_date"]) if pd.notna(row.get("trade_date")) else None,
            fonte=str(row.get("fonte", "asset_intelligence_snapshots")),
            coverage_status=str(row.get("coverage_status", cls._infer_coverage(row))),
        )

    @staticmethod
    def _infer_coverage(row: dict) -> str:
        """Infere coverage_status a partir dos dados disponíveis."""
        sector = row.get("sector")
        if not sector or pd.isna(sector):
            return "needs_sector"
        has_financials = any(
            pd.notna(row.get(c))
            for c in ["fundamental_quality_score", "financial_health_score",
                      "profitability_score", "growth_score", "leverage_score"]
        )
        if not has_financials:
            return "needs_data"
        return "partial"


# ── Leitura ────────────────────────────────────────────────────────────────────

def _db_path() -> str:
    import os, sqlite3
    db_env = os.environ.get("SCANNER_QUANT_DB")
    if db_env and sqlite3.complete_statement(db_env):
        return db_env
    return "scanner_quant.db"


def _load_from_asset_intelligence(db_path: str, tickers: list[str] | None = None) -> pd.DataFrame:
    """Lê setor, subsector e scores fundamentais de asset_intelligence_snapshots."""
    rows = read_table(db_path, "asset_intelligence_snapshots", _VALUATION_INPUT_RAW_COLS, order_by="id DESC", limit=5000)
    if rows.empty:
        return pd.DataFrame(columns=VALUATION_INPUT_COLUMNS)
    rows = filter_tickers(rows, tickers)
    if not rows.empty:
        rows = rows.sort_values(["ticker", "trade_date"], ascending=[True, False]).groupby("ticker", as_index=False).first()
    for col in VALUATION_INPUT_COLUMNS:
        if col not in rows.columns:
            rows[col] = pd.NA
    rows["fonte"] = "asset_intelligence_snapshots"
    # Inferir coverage_status
    rows["coverage_status"] = rows.apply(
        lambda r: ValuationInputs._infer_coverage(r.to_dict()), axis=1
    )
    return rows[VALUATION_INPUT_COLUMNS]


def _load_sector_from_cotahist(db_path: str, tickers: list[str] | None) -> pd.DataFrame:
    """Fallback: tenta setor de cotahist_daily (company_name extraction)."""
    rows = read_table(db_path, "cotahist_daily", ["ticker", "company_name"], order_by="trade_date DESC", limit=50000)
    if rows.empty:
        return pd.DataFrame(columns=VALUATION_INPUT_COLUMNS)
    rows = filter_tickers(rows, tickers)
    if rows.empty:
        return pd.DataFrame(columns=VALUATION_INPUT_COLUMNS)
    rows = rows.groupby("ticker", as_index=False).first()
    rows["fonte"] = "cotahist_daily"
    rows["coverage_status"] = "needs_sector"
    for col in VALUATION_INPUT_COLUMNS:
        if col not in rows.columns:
            rows[col] = pd.NA
    return rows[VALUATION_INPUT_COLUMNS]


# ── Interface pública ──────────────────────────────────────────────────────────

def load_valuation_inputs(ticker: str, db_path: str | None = None) -> ValuationInputs:
    """
    Carrega inputs para valuation de UM ticker.

    Retorna ValuationInputs com coverage_status='empty' quando não há dados.

    Parameters
    ----------
    ticker: str
        Código do ativo B3 (ex: "PETR4")
    db_path: str | None
        Caminho do banco. Usa scanner_quant.db se None.

    Returns
    -------
    ValuationInputs
        Inputs canônicos para o ticker.
    """
    db = db_path or _db_path()
    ticker_upper = str(ticker).strip().upper()

    df = _load_from_asset_intelligence(db, [ticker_upper])
    if not df.empty:
        return ValuationInputs.from_row(df.iloc[0].to_dict())

    df_cotahist = _load_sector_from_cotahist(db, [ticker_upper])
    if not df_cotahist.empty:
        return ValuationInputs.from_row(df_cotahist.iloc[0].to_dict())

    return ValuationInputs.empty(ticker_upper)


def list_valuation_inputs(tickers: list[str] | None = None, db_path: str | None = None) -> pd.DataFrame:
    """
    Lista inputs de valuation para múltiplos tickers.

    Tickers sem dados são incluídos com coverage_status='empty'.
    """
    db = db_path or _db_path()
    df = _load_from_asset_intelligence(db, tickers)

    if df.empty and tickers:
        # Tenta cotahist para cobertura mínima de setor
        df_cotahist = _load_sector_from_cotahist(db, tickers)
        if not df_cotahist.empty:
            df = df_cotahist

    if df.empty:
        return pd.DataFrame(columns=VALUATION_INPUT_COLUMNS)

    return df.reset_index(drop=True)


__all__ = [
    "ValuationInputs",
    "VALUATION_INPUT_COLUMNS",
    "load_valuation_inputs",
    "list_valuation_inputs",
]