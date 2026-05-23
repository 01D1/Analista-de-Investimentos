"""Persistencia do deep dive OOS de hipoteses."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = [
    "id",
    "created_at",
    "hypotheses_count",
    "start_date",
    "end_date",
    "status",
    "best_hypothesis_id",
    "approved_count",
    "blocked_count",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "signal_source",
    "cost_scenario",
    "slippage_scenario",
    "regime",
    "ticker",
    "windows_count",
    "trades_count",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "positive_improvement_pct",
    "block_reason",
    "governance_status",
    "metadata_json",
]

BLOCK_REASON_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "primary_block_reason",
    "secondary_block_reason",
    "explanation",
    "required_actions_json",
    "metadata_json",
]


def save_hypothesis_deep_oos_run(
    db_path: str | Path,
    results_df: pd.DataFrame,
    block_reasons_df: pd.DataFrame | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    metadata: dict | None = None,
) -> int:
    init_database(db_path, verbose=False)
    results = results_df.copy() if results_df is not None else pd.DataFrame()
    reasons = block_reasons_df.copy() if block_reasons_df is not None else pd.DataFrame()
    if not results.empty and "governance_status" in results.columns and "hypothesis_id" in results.columns:
        statuses = results.groupby("hypothesis_id")["governance_status"].first().astype(str)
    else:
        statuses = pd.Series(dtype=str)
    approved_count = int(statuses.eq("HYPOTHESIS_DEEP_APPROVED_FOR_OBSERVATION").sum())
    blocked_count = int(statuses.str.startswith("HYPOTHESIS_DEEP_BLOCKED").sum() + statuses.eq("HYPOTHESIS_DEEP_REJECTED").sum())
    best_hypothesis_id = ""
    if not results.empty:
        grouped = results.groupby("hypothesis_id")["positive_improvement_pct"].mean().sort_values(ascending=False)
        best_hypothesis_id = str(grouped.index[0]) if not grouped.empty else ""
    run_row = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypotheses_count": int(results["hypothesis_id"].nunique()) if not results.empty and "hypothesis_id" in results.columns else 0,
        "start_date": start_date,
        "end_date": end_date,
        "status": "DEEP_OOS_COMPLETED" if not results.empty else "DEEP_OOS_EMPTY",
        "best_hypothesis_id": best_hypothesis_id,
        "approved_count": approved_count,
        "blocked_count": blocked_count,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([run_row]).to_sql("paper_hypothesis_deep_oos_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not results.empty:
            out = results.copy()
            out["run_id"] = run_id
            for col in RESULT_COLUMNS:
                if col not in out.columns and col != "id":
                    out[col] = pd.NA
            out[[c for c in RESULT_COLUMNS if c != "id"]].to_sql("paper_hypothesis_deep_oos_results", con, if_exists="append", index=False)
        if not reasons.empty:
            out_reasons = reasons.copy()
            out_reasons["run_id"] = run_id
            for col in BLOCK_REASON_COLUMNS:
                if col not in out_reasons.columns and col != "id":
                    out_reasons[col] = pd.NA
            out_reasons[[c for c in BLOCK_REASON_COLUMNS if c != "id"]].to_sql("paper_hypothesis_block_reasons", con, if_exists="append", index=False)
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
            if run_id is not None and table != "paper_hypothesis_deep_oos_runs":
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


def load_hypothesis_deep_oos_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_deep_oos_runs", RUN_COLUMNS, limit=limit)


def load_hypothesis_deep_oos_results(db_path: str | Path, run_id: int | None = None, limit: int = 2000) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_deep_oos_results", RESULT_COLUMNS, run_id=run_id, limit=limit)


def load_hypothesis_block_reasons(db_path: str | Path, run_id: int | None = None, limit: int = 2000) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_block_reasons", BLOCK_REASON_COLUMNS, run_id=run_id, limit=limit)
