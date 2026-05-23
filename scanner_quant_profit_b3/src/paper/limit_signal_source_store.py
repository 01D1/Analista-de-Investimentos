"""Persistência da calibração LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "id",
    "created_at",
    "variants_count",
    "start_date",
    "end_date",
    "best_variant_id",
    "approved_count",
    "rejected_count",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "variant_id",
    "signal_source",
    "cost_scenario",
    "slippage_scenario",
    "regime",
    "windows_count",
    "trades_count",
    "remaining_signals",
    "removed_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "mean_cost_drag_delta",
    "mean_slippage_delta",
    "positive_improvement_pct",
    "variant_robustness_score",
    "variant_class",
    "governance_status",
    "metadata_json",
]


def save_limit_signal_source_variant_run(db_path: str | Path, ranked_df: pd.DataFrame, oos_df: pd.DataFrame | None = None, start_date: str | None = None, end_date: str | None = None, metadata: dict | None = None) -> int:
    init_database(db_path, verbose=False)
    ranked = ranked_df.copy() if ranked_df is not None else pd.DataFrame()
    oos = oos_df.copy() if oos_df is not None else pd.DataFrame()
    best = ranked.iloc[0].to_dict() if not ranked.empty else {}
    statuses = ranked.get("governance_status", pd.Series(dtype=str)).astype(str)
    run_row = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        "variants_count": int(ranked["variant_id"].nunique()) if not ranked.empty else 0,
        "start_date": start_date,
        "end_date": end_date,
        "best_variant_id": best.get("variant_id", ""),
        "approved_count": int(statuses.eq("LIMIT_SOURCE_APPROVED_FOR_OBSERVATION").sum()),
        "rejected_count": int(statuses.str.startswith("LIMIT_SOURCE_BLOCKED").sum() + statuses.eq("LIMIT_SOURCE_REJECTED").sum()),
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([run_row]).to_sql("limit_signal_source_variant_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not oos.empty:
            score_cols = ranked[["variant_id", "variant_robustness_score", "variant_class", "governance_status"]].drop_duplicates("variant_id") if not ranked.empty else pd.DataFrame()
            out = oos.merge(score_cols, on="variant_id", how="left") if not score_cols.empty else oos.copy()
            out["run_id"] = run_id
            for col in RESULT_COLUMNS:
                if col not in out.columns and col != "id":
                    out[col] = pd.NA
            out[[c for c in RESULT_COLUMNS if c != "id"]].to_sql("limit_signal_source_variant_results", con, if_exists="append", index=False)
    return run_id


def _read(db_path: str | Path, table: str, columns: list[str], run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame(columns=columns)
            sql = f"SELECT * FROM {table}"
            params = []
            if run_id is not None and table.endswith("_results"):
                sql += " WHERE run_id = ?"
                params.append(int(run_id))
            sql += " ORDER BY id DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(int(limit))
            df = pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def load_limit_signal_source_variant_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "limit_signal_source_variant_runs", RUN_COLUMNS, limit=limit)


def load_limit_signal_source_variant_results(db_path: str | Path, run_id: int | None = None, limit: int = 2000) -> pd.DataFrame:
    return _read(db_path, "limit_signal_source_variant_results", RESULT_COLUMNS, run_id=run_id, limit=limit)
