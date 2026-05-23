"""Persistência dos diffs de inteligência integrada."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


DIFF_COLUMNS = [
    "id",
    "created_at",
    "ticker",
    "previous_snapshot_id",
    "current_snapshot_id",
    "previous_created_at",
    "current_created_at",
    "changes_count",
    "changed_fields_json",
    "score_delta",
    "data_quality_delta",
    "status_changed",
    "governance_changed",
    "valuation_changed",
    "technical_changed",
    "quant_changed",
    "event_changed",
    "regime_changed",
    "options_changed",
    "material_change",
    "material_change_type",
    "explanation",
    "metadata_json",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=DIFF_COLUMNS)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if "changed_fields" in out.columns:
        out["changed_fields_json"] = out["changed_fields"].map(lambda v: json.dumps(v if isinstance(v, list) else [], ensure_ascii=False))
    for col in [
        "status_changed",
        "governance_changed",
        "valuation_changed",
        "technical_changed",
        "quant_changed",
        "event_changed",
        "regime_changed",
        "options_changed",
        "material_change",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(False).astype(int)
    for col in DIFF_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[[c for c in DIFF_COLUMNS if c != "id"]]


def save_asset_intelligence_diffs(db_path: str | Path, diff_df: pd.DataFrame) -> int:
    if diff_df is None or diff_df.empty:
        return 0
    init_database(db_path, verbose=False)
    save = _prepare(diff_df)
    with sqlite3.connect(db_path) as con:
        save.to_sql("asset_intelligence_diffs", con, if_exists="append", index=False)
    return int(len(save))


def _read(db_path: str | Path, where: str = "", params: tuple | None = None, limit: int = 500) -> pd.DataFrame:
    if not Path(db_path).exists():
        return _empty()
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='asset_intelligence_diffs'").fetchone()
            if not exists:
                return _empty()
            sql = f"SELECT {', '.join(DIFF_COLUMNS)} FROM asset_intelligence_diffs"
            if where:
                sql += f" WHERE {where}"
            sql += " ORDER BY created_at DESC, id DESC"
            if limit:
                sql += f" LIMIT {int(limit)}"
            df = pd.read_sql_query(sql, con, params=params or ())
    except sqlite3.Error:
        return _empty()
    for col in DIFF_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[DIFF_COLUMNS]


def load_latest_asset_intelligence_diffs(db_path: str | Path, tickers: list[str] | None = None) -> pd.DataFrame:
    df = _read(db_path, limit=5000)
    if df.empty:
        return df
    if tickers:
        allowed = {str(t).upper() for t in tickers}
        df = df[df["ticker"].astype(str).str.upper().isin(allowed)].copy()
    if df.empty:
        return _empty()
    return df.sort_values(["ticker", "created_at", "id"], ascending=[True, False, False]).groupby("ticker", as_index=False).first()


def load_asset_intelligence_diff_history(db_path: str | Path, ticker: str | None = None, limit: int = 500) -> pd.DataFrame:
    where = "ticker = ?" if ticker else ""
    params = (str(ticker).upper(),) if ticker else None
    return _read(db_path, where=where, params=params, limit=limit)
