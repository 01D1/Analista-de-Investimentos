"""Persistencia da auditoria de fontes de dados."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.source_inventory import TRACEABILITY_COLUMNS
from src.db.init_db import init_database


AUDIT_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "sources_checked",
    "ok_count",
    "warning_count",
    "error_count",
    "missing_count",
    "overall_reliability_score",
    "overall_status",
    "metadata_json",
]

AUDIT_RESULT_DB_COLUMNS = [
    "id",
    "run_id",
    "source_name",
    "source_type",
    "primary_or_secondary",
    "available",
    "records_count",
    "latest_date",
    "tickers_count",
    "coverage_scope",
    "status",
    "reliability_score",
    "reliability_class",
    "message",
    "metadata_json",
]


def save_data_source_audit_run(db_path: str | Path, run_summary: dict, results_df: pd.DataFrame) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    started_at = run_summary.get("started_at") or datetime.now().isoformat(timespec="seconds")
    finished_at = run_summary.get("finished_at") or datetime.now().isoformat(timespec="seconds")
    metadata = run_summary.get("metadata_json")
    if not isinstance(metadata, str):
        metadata = json.dumps(run_summary.get("metadata", {}), ensure_ascii=False, default=str)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO data_source_audit_runs (
                started_at, finished_at, status, sources_checked, ok_count,
                warning_count, error_count, missing_count, overall_reliability_score,
                overall_status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                finished_at,
                run_summary.get("status", run_summary.get("overall_status", "UNKNOWN")),
                int(run_summary.get("sources_checked", len(results_df) if results_df is not None else 0) or 0),
                int(run_summary.get("ok_count", 0) or 0),
                int(run_summary.get("warning_count", 0) or 0),
                int(run_summary.get("error_count", 0) or 0),
                int(run_summary.get("missing_count", 0) or 0),
                float(run_summary.get("overall_reliability_score", 0) or 0),
                run_summary.get("overall_status", "UNKNOWN"),
                metadata,
            ),
        )
        run_id = int(cur.lastrowid)
        if results_df is not None and not results_df.empty:
            rows = []
            for _, row in results_df.iterrows():
                rows.append(
                    (
                        run_id,
                        row.get("source_name"),
                        row.get("source_type"),
                        row.get("primary_or_secondary"),
                        1 if bool(row.get("available")) else 0,
                        int(row.get("records_count") or 0),
                        row.get("latest_date"),
                        int(row.get("tickers_count") or 0),
                        row.get("coverage_scope"),
                        row.get("status"),
                        float(row.get("reliability_score") or 0),
                        row.get("reliability_class"),
                        row.get("message"),
                        row.get("metadata_json"),
                    )
                )
            con.executemany(
                """
                INSERT INTO data_source_audit_results (
                    run_id, source_name, source_type, primary_or_secondary, available,
                    records_count, latest_date, tickers_count, coverage_scope, status,
                    reliability_score, reliability_class, message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        con.commit()
    return run_id


def load_latest_data_source_audit(db_path: str | Path) -> dict[str, pd.DataFrame]:
    db_path = Path(db_path)
    if not db_path.exists():
        return {"run": pd.DataFrame(columns=AUDIT_RUN_COLUMNS), "results": pd.DataFrame(columns=AUDIT_RESULT_DB_COLUMNS)}
    try:
        with sqlite3.connect(db_path) as con:
            run = pd.read_sql_query("SELECT * FROM data_source_audit_runs ORDER BY id DESC LIMIT 1", con)
            if run.empty:
                return {"run": run, "results": pd.DataFrame(columns=AUDIT_RESULT_DB_COLUMNS)}
            results = pd.read_sql_query("SELECT * FROM data_source_audit_results WHERE run_id = ? ORDER BY id", con, params=(int(run.iloc[0]["id"]),))
            return {"run": run, "results": results}
    except Exception:
        return {"run": pd.DataFrame(columns=AUDIT_RUN_COLUMNS), "results": pd.DataFrame(columns=AUDIT_RESULT_DB_COLUMNS)}


def load_data_source_audit_history(db_path: str | Path, source_name: str | None = None, limit: int = 100) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=AUDIT_RESULT_DB_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            sql = "SELECT * FROM data_source_audit_results"
            params: list = []
            if source_name:
                sql += " WHERE source_name = ?"
                params.append(source_name)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame(columns=AUDIT_RESULT_DB_COLUMNS)


def save_traceability_records(db_path: str | Path, traceability_df: pd.DataFrame) -> int:
    if traceability_df is None or traceability_df.empty:
        return 0
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    df = traceability_df.copy()
    for col in TRACEABILITY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    with sqlite3.connect(db_path) as con:
        df[TRACEABILITY_COLUMNS].to_sql("data_source_traceability", con, if_exists="append", index=False)
    return len(df)

