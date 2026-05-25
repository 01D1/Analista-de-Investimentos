"""
src/valuation/valuation_coverage.py — Canonical Valuation Coverage Store (S05)

Rastreia quais tickers possuem valuation completo, parcial ou ausente.
Apenas leitura — nunca calcula, nunca cria mock, nunca altera banco.

Este store é usado pelo sector router (S04) para decidir bloqueio/procedência.

D077–D082 intocados. D086 (coexistência) respeitado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from src.integration.connectors._sqlite import empty, filter_tickers, read_table

# ── Coverage status ──────────────────────────────────────────────────────────────

class CoverageStatus:
    READY = "ready"               # Valuation disponível e pronto
    PARTIAL = "partial"           # Setor conhecido, financials parciais
    NEEDS_DATA = "needs_data"     # Setor ok, financials ausentes
    NEEDS_SECTOR = "needs_sector" # Setor não identificado
    EMPTY = "empty"               # Nenhum dado disponível
    LEGACY_TICKER = "legacy_ticker"  # Ticker extinto por corporate action (fusão/renomeação/delisting)
                                     # → router BLOQUEADO; usar successor_ticker para cobertura ativa


# ── Colunas canônicas ──────────────────────────────────────────────────────────

VALUATION_COVERAGE_COLUMNS = [
    "ticker",
    "sector",
    "coverage_status",
    "has_fair_value",
    "has_financials",
    "has_sector",
    "valuation_available",
    "ri_docs_count",
    "last_updated",
    "fonte",
]


# ── Sentinel ────────────────────────────────────────────────────────────────────

@dataclass
class ValuationCoverage:
    """Status de cobertura de valuation para um ticker."""

    ticker: str
    sector: Optional[str] = None
    coverage_status: str = CoverageStatus.EMPTY
    has_fair_value: bool = False
    has_financials: bool = False
    has_sector: bool = False
    valuation_available: bool = False
    ri_docs_count: int = 0
    last_updated: Optional[str] = None
    fonte: str = "asset_intelligence_snapshots"

    @classmethod
    def empty(cls, ticker: str) -> "ValuationCoverage":
        return cls(ticker=ticker, coverage_status=CoverageStatus.EMPTY)

    @classmethod
    def from_row(cls, row: dict) -> "ValuationCoverage":
        return cls(
            ticker=str(row.get("ticker", "")).strip().upper(),
            sector=str(row["sector"]) if pd.notna(row.get("sector")) else None,
            coverage_status=str(row.get("coverage_status", CoverageStatus.EMPTY)),
            has_fair_value=bool(row.get("has_fair_value", False)),
            has_financials=bool(row.get("has_financials", False)),
            has_sector=bool(row.get("has_sector", False)),
            valuation_available=bool(row.get("valuation_available", False)),
            ri_docs_count=int(row.get("ri_docs_count", 0)),
            last_updated=str(row.get("last_updated")) if pd.notna(row.get("last_updated")) else None,
            fonte=str(row.get("fonte", "asset_intelligence_snapshots")),
        )

    def to_status(self) -> str:
        """Retorna status compatível com router (lowercase)."""
        return self.coverage_status.lower()


# ── Leitura ────────────────────────────────────────────────────────────────────

def _db_path() -> str:
    import os, sqlite3
    db_env = os.environ.get("SCANNER_QUANT_DB")
    if db_env and sqlite3.complete_statement(db_env):
        return db_env
    return "scanner_quant.db"


def _load_from_asset_intelligence(db_path: str, tickers: list[str] | None = None) -> pd.DataFrame:
    """Agrega sector + fair_value + financials de asset_intelligence_snapshots."""
    cols = ["ticker", "sector", "trade_date", "valuation_available",
            "fair_value", "fundamental_quality_score", "financial_health_score",
            "profitability_score", "growth_score", "leverage_score"]
    df = read_table(db_path, "asset_intelligence_snapshots", cols, order_by="id DESC", limit=5000)
    if df.empty:
        return pd.DataFrame(columns=VALUATION_COVERAGE_COLUMNS)
    df = filter_tickers(df, tickers)
    if not df.empty:
        df = df.sort_values(["ticker", "trade_date"], ascending=[True, False]).groupby("ticker", as_index=False).first()

    financial_cols = ["fundamental_quality_score", "financial_health_score",
                      "profitability_score", "growth_score", "leverage_score"]
    df["has_financials"] = df[financial_cols].notna().any(axis=1)
    df["has_sector"] = df["sector"].notna()
    df["has_fair_value"] = df["fair_value"].notna()
    df["valuation_available"] = df["valuation_available"].fillna(0).astype(bool)

    def _infer_status(row):
        if not row.get("has_sector", False):
            return CoverageStatus.NEEDS_SECTOR
        if not row.get("has_financials", False):
            return CoverageStatus.NEEDS_DATA
        if row.get("valuation_available", False) or row.get("has_fair_value", False):
            return CoverageStatus.READY
        return CoverageStatus.PARTIAL

    df["coverage_status"] = df.apply(_infer_status, axis=1)
    df["last_updated"] = df["trade_date"]
    df["fonte"] = "asset_intelligence_snapshots"
    df["ri_docs_count"] = 0  # calculado abaixo se necessário

    for col in VALUATION_COVERAGE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[VALUATION_COVERAGE_COLUMNS]


def _load_ri_docs_count(db_path: str, tickers: list[str] | None) -> dict[str, int]:
    """Conta documentos CVM por ticker em ri_documents."""
    df = read_table(db_path, "ri_documents", ["ticker", "id"], order_by="published_at DESC", limit=100000)
    if df.empty:
        return {}
    df = filter_tickers(df, tickers)
    if df.empty:
        return {}
    counts = df.groupby("ticker").size().to_dict()
    return {t.upper(): int(c) for t, c in counts.items()}


# ── Interface pública ──────────────────────────────────────────────────────────

def load_valuation_coverage(ticker: str, db_path: str | None = None) -> ValuationCoverage:
    """
    Carrega status de cobertura para UM ticker.

    Returns
    -------
    ValuationCoverage
        Status canônico de cobertura.
    """
    db = db_path or _db_path()
    ticker_upper = str(ticker).strip().upper()

    df = _load_from_asset_intelligence(db, [ticker_upper])
    if not df.empty:
        result = ValuationCoverage.from_row(df.iloc[0].to_dict())
        # Complementar com contagem de ri_documents
        ri_counts = _load_ri_docs_count(db, [ticker_upper])
        result.ri_docs_count = ri_counts.get(ticker_upper, 0)
        if result.ri_docs_count == 0 and result.coverage_status == CoverageStatus.EMPTY:
            result.fonte = "no_data"
        return result

    return ValuationCoverage.empty(ticker_upper)


def load_valuation_coverage_batch(tickers: list[str], db_path: str | None = None) -> pd.DataFrame:
    """
    Lista status de cobertura para múltiplos tickers.

    Tickers sem dados são incluídos com coverage_status='empty'.
    """
    db = db_path or _db_path()
    ticker_set = {str(t).upper().strip() for t in tickers}
    if not ticker_set:
        return pd.DataFrame(columns=VALUATION_COVERAGE_COLUMNS)

    # ── Tentativa 1: asset_intelligence_snapshots ──
    df = _load_from_asset_intelligence(db, tickers)

    # ── Tentativa 2: outputs fallback via list_valuation_results (S05-DB-01) ──
    if df.empty:
        from src.valuation.valuation_results import list_valuation_results as _list_results
        df_results = _list_results(list(ticker_set), db)
        if not df_results.empty:
            rows = []
            for _, r in df_results.iterrows():
                rows.append({
                    "ticker": str(r.get("ticker", "")).upper(),
                    "sector": None,
                    "coverage_status": CoverageStatus.PARTIAL,
                    "has_fair_value": pd.notna(r.get("fair_value")),
                    "has_financials": False,
                    "has_sector": False,
                    "valuation_available": bool(r.get("valuation_available", False)),
                    "ri_docs_count": 0,
                    "last_updated": r.get("data_valuation"),
                    "fonte": r.get("fonte", "outputs/excel"),
                })
            if rows:
                df = pd.DataFrame(rows)
                for col in VALUATION_COVERAGE_COLUMNS:
                    if col not in df.columns:
                        df[col] = pd.NA
                df = df[VALUATION_COVERAGE_COLUMNS]
                # Completar tickers ausentes com empty
                covered = set(df["ticker"].str.upper())
                missing = ticker_set - covered
                if missing:
                    missing_rows = [{"ticker": t, "coverage_status": CoverageStatus.EMPTY} for t in missing]
                    df_missing = pd.DataFrame(missing_rows)
                    for col in VALUATION_COVERAGE_COLUMNS:
                        if col not in df_missing.columns:
                            df_missing[col] = pd.NA
                    df = pd.concat([df, df_missing[df_missing.columns]], ignore_index=True)
                return df.reset_index(drop=True)

    # ── Preencher tickers não cobertos com empty ──
    if not df.empty:
        covered = set(df["ticker"].str.upper())
        missing = ticker_set - covered
        if missing:
            missing_rows = [{"ticker": t, "coverage_status": CoverageStatus.EMPTY} for t in missing]
            df_missing = pd.DataFrame(missing_rows)
            for col in VALUATION_COVERAGE_COLUMNS:
                if col not in df_missing.columns:
                    df_missing[col] = pd.NA
            df = pd.concat([df, df_missing[df_missing.columns]], ignore_index=True)
    else:
        # Nenhuma fonte retornou dados → empty para todos
        rows = [{"ticker": t, "coverage_status": CoverageStatus.EMPTY} for t in ticker_set]
        df = pd.DataFrame(rows)
        for col in VALUATION_COVERAGE_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

    return df[VALUATION_COVERAGE_COLUMNS].reset_index(drop=True)


__all__ = [
    "CoverageStatus",
    "ValuationCoverage",
    "VALUATION_COVERAGE_COLUMNS",
    "load_valuation_coverage",
    "load_valuation_coverage_batch",
]