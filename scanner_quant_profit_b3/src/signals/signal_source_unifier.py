"""Normalização de fontes de sinal para paper trading e validação."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


UNIFIED_COLUMNS = [
    "signal_id",
    "trade_date",
    "ticker",
    "signal_source",
    "signal_type",
    "signal_score",
    "signal_confidence",
    "direction",
    "governance_status",
    "reason",
    "metadata_json",
]


def _read(db_path: str | Path, table: str, columns: list[str]) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame()
            existing = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
            selected = [c for c in columns if c in existing]
            if not selected:
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT {', '.join(selected)} FROM {table}", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _filter(df: pd.DataFrame, start_date=None, end_date=None, tickers=None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.date.astype(str)
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    if start_date:
        out = out[out["trade_date"] >= str(start_date)]
    if end_date:
        out = out[out["trade_date"] <= str(end_date)]
    if tickers:
        allowed = {str(t).upper() for t in tickers}
        out = out[out["ticker"].isin(allowed)]
    return out


def _ensure(df: pd.DataFrame) -> pd.DataFrame:
    for col in UNIFIED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[UNIFIED_COLUMNS]


def load_quant_signals_for_paper(db_path, start_date=None, end_date=None, tickers=None) -> pd.DataFrame:
    df = _read(db_path, "historical_backtest_results", ["id", "trade_date", "ticker", "score_final", "signal_type", "signal_confidence", "explanation", "metadata_json"])
    df = _filter(df, start_date, end_date, tickers)
    if df.empty:
        return _ensure(pd.DataFrame())
    out = pd.DataFrame(
        {
            "signal_id": "quant:" + df["id"].astype(str),
            "trade_date": df["trade_date"],
            "ticker": df["ticker"],
            "signal_source": "quant",
            "signal_type": df.get("signal_type"),
            "signal_score": pd.to_numeric(df.get("score_final"), errors="coerce"),
            "signal_confidence": df.get("signal_confidence"),
            "direction": "ESTUDO",
            "governance_status": "SIGNAL_SOURCE_IN_STUDY",
            "reason": df.get("explanation"),
            "metadata_json": df.get("metadata_json", "{}"),
        }
    )
    return _ensure(out)


def load_technical_signals_for_paper(db_path, start_date=None, end_date=None, tickers=None) -> pd.DataFrame:
    df = _read(db_path, "technical_setup_signals", ["id", "trade_date", "ticker", "setup_type", "setup_score", "setup_confidence", "setup_direction", "governance_status", "explanation", "metadata_json"])
    df = _filter(df, start_date, end_date, tickers)
    if df.empty:
        return _ensure(pd.DataFrame())
    out = pd.DataFrame(
        {
            "signal_id": "technical:" + df["id"].astype(str),
            "trade_date": df["trade_date"],
            "ticker": df["ticker"],
            "signal_source": "technical",
            "signal_type": df.get("setup_type"),
            "signal_score": pd.to_numeric(df.get("setup_score"), errors="coerce"),
            "signal_confidence": pd.to_numeric(df.get("setup_confidence"), errors="coerce"),
            "direction": df.get("setup_direction", "ESTUDO"),
            "governance_status": df.get("governance_status"),
            "reason": df.get("explanation"),
            "metadata_json": df.get("metadata_json", "{}"),
        }
    )
    return _ensure(out)


def load_integrated_signals_for_paper(db_path, start_date=None, end_date=None, tickers=None) -> pd.DataFrame:
    df = _read(db_path, "asset_intelligence_snapshots", ["id", "trade_date", "ticker", "integrated_score", "integrated_status", "integrated_confidence", "integrated_governance_status", "explanation", "metadata_json"])
    df = _filter(df, start_date, end_date, tickers)
    if df.empty:
        return _ensure(pd.DataFrame())
    out = pd.DataFrame(
        {
            "signal_id": "integrated:" + df["id"].astype(str),
            "trade_date": df["trade_date"],
            "ticker": df["ticker"],
            "signal_source": "integrated",
            "signal_type": df.get("integrated_status"),
            "signal_score": pd.to_numeric(df.get("integrated_score"), errors="coerce"),
            "signal_confidence": df.get("integrated_confidence"),
            "direction": "ESTUDO",
            "governance_status": df.get("integrated_governance_status"),
            "reason": df.get("explanation"),
            "metadata_json": df.get("metadata_json", "{}"),
        }
    )
    return _ensure(out)


def unify_signals_for_paper(signals_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for source, df in (signals_dict or {}).items():
        if df is None or df.empty:
            continue
        out = _ensure(df.copy())
        out["signal_source"] = out["signal_source"].fillna(str(source).lower())
        frames.append(out)
    if not frames:
        return _ensure(pd.DataFrame())
    unified = pd.concat(frames, ignore_index=True)
    unified["metadata_json"] = unified["metadata_json"].fillna("{}").map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v or "{}"))
    return unified.sort_values(["trade_date", "ticker", "signal_source", "signal_id"]).drop_duplicates(["trade_date", "ticker", "signal_source", "signal_type"])


def validate_unified_signals(signals_df: pd.DataFrame) -> dict:
    issues = []
    if signals_df is None or signals_df.empty:
        return {"valid": False, "status": "COVERAGE_INSUFFICIENT", "issues": ["sem sinais unificados"], "rows_count": 0}
    df = signals_df.copy()
    missing = [c for c in UNIFIED_COLUMNS if c not in df.columns]
    if missing:
        issues.append("colunas ausentes: " + ", ".join(missing))
    dates = pd.to_datetime(df.get("trade_date"), errors="coerce")
    if dates.isna().any():
        issues.append("datas inválidas")
    if df.get("ticker", pd.Series(dtype=str)).astype(str).str.strip().eq("").any():
        issues.append("tickers inválidos")
    scores = pd.to_numeric(df.get("signal_score"), errors="coerce")
    if scores.notna().any() and ((scores.dropna() < 0) | (scores.dropna() > 100)).any():
        issues.append("score fora de 0-100")
    allowed = {"quant", "technical", "integrated", "options"}
    invalid_sources = set(df.get("signal_source", pd.Series(dtype=str)).dropna().astype(str).str.lower()) - allowed
    if invalid_sources:
        issues.append("fonte inválida: " + ", ".join(sorted(invalid_sources)))
    dup_cols = ["trade_date", "ticker", "signal_source", "signal_type"]
    if all(c in df.columns for c in dup_cols) and df.duplicated(dup_cols).any():
        issues.append("duplicidade de sinal")
    return {"valid": not issues, "status": "VALID_UNIFIED_SIGNALS" if not issues else "INVALID_UNIFIED_SIGNALS", "issues": issues, "rows_count": int(len(df))}

