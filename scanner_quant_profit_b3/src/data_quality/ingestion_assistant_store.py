"""Persistencia do assistente operacional de ingestao."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


def save_ingestion_assistant_run(db_path: str | Path, summary: dict, steps_df: pd.DataFrame, validation_df: pd.DataFrame | None = None, comparison_df: pd.DataFrame | None = None) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO ingestion_assistant_runs (
                started_at, finished_at, dry_run, executed, status, sources,
                steps_total, steps_executed, steps_failed, manual_steps,
                improvements_count, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.get("started_at", datetime.now().isoformat(timespec="seconds")),
                summary.get("finished_at", datetime.now().isoformat(timespec="seconds")),
                1 if summary.get("dry_run", True) else 0,
                1 if summary.get("executed", False) else 0,
                summary.get("status", "UNKNOWN"),
                summary.get("sources", ""),
                int(summary.get("steps_total", 0) or 0),
                int(summary.get("steps_executed", 0) or 0),
                int(summary.get("steps_failed", 0) or 0),
                int(summary.get("manual_steps", 0) or 0),
                int(summary.get("improvements_count", 0) or 0),
                json.dumps(summary.get("metadata", {}), ensure_ascii=False, default=str),
            ),
        )
        run_id = int(cur.lastrowid)
        if steps_df is not None and not steps_df.empty:
            rows = []
            for _, row in steps_df.iterrows():
                rows.append(
                    (
                        run_id,
                        row.get("step_id"),
                        int(row.get("step_order") or 0),
                        row.get("source_domain"),
                        row.get("step_type"),
                        row.get("title"),
                        row.get("suggested_command"),
                        1 if bool(row.get("can_execute")) else 0,
                        1 if bool(row.get("requires_confirm")) else 0,
                        row.get("risk_level"),
                        row.get("status"),
                        row.get("stdout", ""),
                        row.get("stderr", ""),
                        row.get("metadata_json"),
                    )
                )
            con.executemany(
                """
                INSERT INTO ingestion_assistant_steps (
                    run_id, step_id, step_order, source_domain, step_type, title,
                    suggested_command, can_execute, requires_confirm, risk_level,
                    status, stdout, stderr, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        if validation_df is not None and not validation_df.empty:
            rows = []
            for _, row in validation_df.iterrows():
                rows.append((run_id, row.get("source_domain"), row.get("validation_status"), row.get("before_status"), row.get("after_status"), 1 if bool(row.get("improvement_detected")) else 0, int(row.get("records_before") or 0), int(row.get("records_after") or 0), row.get("latest_date_before"), row.get("latest_date_after"), row.get("message"), row.get("metadata_json")))
            con.executemany(
                """
                INSERT INTO post_ingestion_validation_results (
                    run_id, source_domain, validation_status, before_status, after_status,
                    improvement_detected, records_before, records_after,
                    latest_date_before, latest_date_after, message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        if comparison_df is not None and not comparison_df.empty:
            rows = []
            for _, row in comparison_df.iterrows():
                rows.append((run_id, row.get("source_name"), float(row.get("before_score") or 0), float(row.get("after_score") or 0), float(row.get("score_delta") or 0), row.get("before_status"), row.get("after_status"), 1 if bool(row.get("status_improved")) else 0, int(row.get("records_delta") or 0), 1 if bool(row.get("freshness_improved")) else 0, row.get("message"), row.get("metadata_json")))
            con.executemany(
                """
                INSERT INTO ingestion_reliability_comparison (
                    run_id, source_name, before_score, after_score, score_delta,
                    before_status, after_status, status_improved, records_delta,
                    freshness_improved, message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        con.commit()
    return run_id


def _load(db_path: str | Path, table: str, where: str = "", params: tuple = (), limit: int | None = None) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame()
    try:
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        sql += " ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        with sqlite3.connect(db_path) as con:
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def load_ingestion_assistant_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _load(db_path, "ingestion_assistant_runs", limit=limit)


def load_ingestion_assistant_steps(db_path: str | Path, run_id: int) -> pd.DataFrame:
    return _load(db_path, "ingestion_assistant_steps", "run_id = ?", (int(run_id),))


def load_post_ingestion_validation(db_path: str | Path, run_id: int) -> pd.DataFrame:
    return _load(db_path, "post_ingestion_validation_results", "run_id = ?", (int(run_id),))


def load_ingestion_comparison(db_path: str | Path, run_id: int) -> pd.DataFrame:
    return _load(db_path, "ingestion_reliability_comparison", "run_id = ?", (int(run_id),))

