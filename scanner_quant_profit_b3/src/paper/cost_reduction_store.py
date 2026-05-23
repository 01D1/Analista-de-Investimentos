"""Persistencia de simulacoes de reducao de custo."""
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
    "base_paper_run_id",
    "variants_count",
    "improved_count",
    "rejected_count",
    "best_variant_id",
    "best_improvement_score",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "variant_id",
    "variant_type",
    "total_return",
    "max_drawdown",
    "trades_count",
    "cost_drag_total",
    "entry_cost",
    "exit_cost",
    "rebalance_cost",
    "cost_reduction",
    "cost_reduction_pct",
    "return_delta",
    "drawdown_delta",
    "turnover_delta",
    "improvement_score",
    "governance_status",
    "metadata_json",
]


def _prepare(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col != "id" and col not in out.columns:
            out[col] = pd.NA
    return out[[c for c in columns if c != "id"]]


def save_cost_reduction_run(db_path: str | Path, base_paper_run_id: int, results_df: pd.DataFrame, metadata: dict | None = None) -> int:
    init_database(db_path, verbose=False)
    results = results_df.copy() if results_df is not None else pd.DataFrame()
    approved = {"COST_REDUCTION_APPROVED_FOR_MORE_TESTING", "COST_REDUCTION_OBSERVATION_ONLY"}
    improved_count = int(results.get("governance_status", pd.Series(dtype=str)).astype(str).isin(approved).sum()) if not results.empty else 0
    rejected_count = int(len(results) - improved_count)
    best = results.sort_values("improvement_score", ascending=False).iloc[0].to_dict() if not results.empty and "improvement_score" in results.columns else {}
    run_row = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        "base_paper_run_id": int(base_paper_run_id),
        "variants_count": int(len(results)),
        "improved_count": improved_count,
        "rejected_count": rejected_count,
        "best_variant_id": best.get("variant_id"),
        "best_improvement_score": best.get("improvement_score"),
        "metadata_json": json.dumps(metadata or {"nao_recomendacao": True}, ensure_ascii=False, default=str),
    }
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([run_row]).to_sql("paper_cost_reduction_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not results.empty:
            results["run_id"] = run_id
            _prepare(results, RESULT_COLUMNS).to_sql("paper_cost_reduction_results", con, if_exists="append", index=False)
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
            if run_id is not None and table != "paper_cost_reduction_runs":
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


def load_cost_reduction_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_cost_reduction_runs", RUN_COLUMNS, limit=limit)


def load_cost_reduction_results(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_cost_reduction_results", RESULT_COLUMNS, run_id=run_id, limit=limit)
