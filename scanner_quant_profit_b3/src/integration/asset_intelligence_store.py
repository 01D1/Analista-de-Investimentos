"""Persistência dos snapshots de inteligência integrada por ativo."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.integration.asset_intelligence_model import ASSET_INTELLIGENCE_COLUMNS, empty_asset_intelligence_frame


DB_COLUMNS = [
    "created_at",
    "trade_date",
    "ticker",
    "company_name",
    "sector",
    "subsector",
    "market_price",
    "technical_score_final",
    "technical_status",
    "top_technical_setup",
    "technical_setup_score",
    "technical_setup_confidence",
    "technical_governance_status",
    "technical_oos_status",
    "technical_explanation",
    "quant_score",
    "quant_signal_type",
    "quant_signal_confidence",
    "quant_governance_status",
    "quant_explanation",
    "valuation_available",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "valuation_governance_status",
    "has_recent_event",
    "event_type",
    "event_context_type",
    "event_impact_score",
    "event_coverage_quality",
    "event_governance_status",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
    "regime_governance_status",
    "option_available",
    "best_option_structure_type",
    "option_structure_score",
    "option_oos_governance_status",
    "option_liquidity_score",
    "option_execution_quality",
    "option_explanation",
    "ensemble_vol",
    "var_95",
    "expected_shortfall_95",
    "recommended_size",
    "recommended_position_value",
    "risk_status",
    "risk_limiting_factor",
    "risk_explanation",
    "integrated_score",
    "integrated_status",
    "integrated_confidence",
    "integrated_governance_status",
    "data_quality_score",
    "governance_blocked",
    "explanation",
    "reasons_for_json",
    "reasons_against_json",
    "required_actions_json",
    "metadata_json",
]


def _json_value(value) -> str | None:
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) or value is None or pd.isna(value):
        return value
    return str(value)


def _prepare_for_db(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rename = {
        "reasons_for": "reasons_for_json",
        "reasons_against": "reasons_against_json",
        "required_actions": "required_actions_json",
    }
    out = out.rename(columns=rename)
    for col in ["reasons_for_json", "reasons_against_json", "required_actions_json", "metadata_json"]:
        if col in out.columns:
            out[col] = out[col].map(_json_value)
    for col in ["valuation_available", "has_recent_event", "option_available", "governance_blocked"]:
        if col in out.columns:
            out[col] = out[col].fillna(False).astype(int)
    for col in DB_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[DB_COLUMNS]


def save_asset_intelligence_snapshot(db_path: str | Path, df: pd.DataFrame) -> int:
    """Salva o snapshot integrado. Retorna a quantidade de ativos gravados."""
    if df.empty:
        return 0
    save = _prepare_for_db(df)
    with sqlite3.connect(db_path) as con:
        save.to_sql("asset_intelligence_snapshots", con, if_exists="append", index=False)
    return int(len(save))


def _read_table(db_path: str | Path, where: str = "", params: Iterable | None = None, limit: int | None = None) -> pd.DataFrame:
    columns = ["id", *DB_COLUMNS]
    if not Path(db_path).exists():
        return empty_asset_intelligence_frame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='asset_intelligence_snapshots'").fetchone() is None:
                return empty_asset_intelligence_frame()
            sql = f"SELECT {', '.join(columns)} FROM asset_intelligence_snapshots"
            if where:
                sql += f" WHERE {where}"
            sql += " ORDER BY created_at DESC, id DESC"
            if limit:
                sql += f" LIMIT {int(limit)}"
            df = pd.read_sql_query(sql, con, params=list(params or []))
    except sqlite3.Error:
        return empty_asset_intelligence_frame()
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def _restore_api_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return empty_asset_intelligence_frame()
    out = df.rename(
        columns={
            "reasons_for_json": "reasons_for",
            "reasons_against_json": "reasons_against",
            "required_actions_json": "required_actions",
        }
    )
    for col in ASSET_INTELLIGENCE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    cols = [c for c in ["id", "created_at"] if c in out.columns] + ASSET_INTELLIGENCE_COLUMNS
    return out[cols]


def load_latest_asset_intelligence_snapshot(db_path: str | Path, tickers: list[str] | None = None) -> pd.DataFrame:
    df = _read_table(db_path, limit=5000)
    if df.empty:
        return empty_asset_intelligence_frame()
    if tickers:
        allowed = {str(t).upper() for t in tickers}
        df = df[df["ticker"].astype(str).str.upper().isin(allowed)].copy()
    if df.empty:
        return empty_asset_intelligence_frame()
    latest = df.sort_values(["ticker", "created_at", "id"], ascending=[True, False, False]).groupby("ticker", as_index=False).first()
    return _restore_api_columns(latest)


def load_asset_intelligence_history(db_path: str | Path, ticker: str | None = None, limit: int = 500) -> pd.DataFrame:
    where = "ticker = ?" if ticker else ""
    params = (str(ticker).upper(),) if ticker else None
    return _restore_api_columns(_read_table(db_path, where=where, params=params, limit=limit))
