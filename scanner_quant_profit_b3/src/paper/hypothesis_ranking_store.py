"""Persistência do ranking multi-fonte de hipóteses."""
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
    "sources_count",
    "scenarios_count",
    "robust_count",
    "promising_count",
    "rejected_count",
    "best_hypothesis_id",
    "best_score",
    "metadata_json",
]

RESULT_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "signal_source",
    "scenario_name",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "cost_sensitivity_flag",
    "overfitting_flag",
    "source_diversity_score",
    "hypothesis_robustness_score",
    "hypothesis_class",
    "governance_status",
    "metadata_json",
]


def save_hypothesis_ranking_run(db_path: str | Path, ranked_df: pd.DataFrame, validation_df: pd.DataFrame | None = None, metadata: dict | None = None) -> int:
    init_database(db_path, verbose=False)
    ranked = ranked_df.copy() if ranked_df is not None else pd.DataFrame()
    validation = validation_df.copy() if validation_df is not None else pd.DataFrame()
    best = ranked.iloc[0].to_dict() if not ranked.empty else {}
    run_row = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypotheses_count": int(ranked["hypothesis_id"].nunique()) if not ranked.empty else 0,
        "sources_count": int(validation["signal_source"].nunique()) if not validation.empty and "signal_source" in validation.columns else int(ranked.get("useful_sources_count", pd.Series(dtype=int)).max() or 0),
        "scenarios_count": int(validation["scenario_name"].nunique()) if not validation.empty and "scenario_name" in validation.columns else 0,
        "robust_count": int(ranked["hypothesis_class"].astype(str).eq("HYPOTHESIS_ROBUST").sum()) if not ranked.empty else 0,
        "promising_count": int(ranked["hypothesis_class"].astype(str).isin(["HYPOTHESIS_PROMISING", "HYPOTHESIS_OBSERVATION_ONLY"]).sum()) if not ranked.empty else 0,
        "rejected_count": int(ranked["hypothesis_class"].astype(str).isin(["HYPOTHESIS_REJECTED", "HYPOTHESIS_FRAGILE", "HYPOTHESIS_INSUFFICIENT_DATA"]).sum()) if not ranked.empty else 0,
        "best_hypothesis_id": best.get("hypothesis_id"),
        "best_score": float(best.get("hypothesis_robustness_score") or 0),
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }
    with sqlite3.connect(db_path) as con:
        pd.DataFrame([run_row]).to_sql("paper_hypothesis_ranking_runs", con, if_exists="append", index=False)
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not ranked.empty:
            out = ranked.copy()
            out["run_id"] = run_id
            for col in RESULT_COLUMNS:
                if col not in out.columns and col != "id":
                    out[col] = pd.NA
            out[[c for c in RESULT_COLUMNS if c != "id"]].to_sql("paper_hypothesis_ranking_results", con, if_exists="append", index=False)
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


def load_hypothesis_ranking_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_ranking_runs", RUN_COLUMNS, limit=limit)


def load_hypothesis_ranking_results(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_hypothesis_ranking_results", RESULT_COLUMNS, run_id=run_id, limit=limit)

