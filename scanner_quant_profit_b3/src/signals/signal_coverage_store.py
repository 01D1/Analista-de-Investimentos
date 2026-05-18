"""Persistência de diagnósticos de cobertura de fontes de sinal."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


RUN_COLUMNS = ["id", "created_at", "start_date", "end_date", "sources_checked", "coverage_status", "useful_cells_pct", "metadata_json"]
SOURCE_COLUMNS = [
    "id",
    "run_id",
    "signal_source",
    "signals_count",
    "tickers_count",
    "active_days_count",
    "regimes_count",
    "useful_cells_count",
    "coverage_pct",
    "coverage_status",
    "requirements_status",
    "metadata_json",
]


def save_signal_coverage_run(
    db_path: str | Path,
    coverage_df: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
    sources_checked: list[str] | None = None,
    metadata: dict | None = None,
) -> int:
    init_database(db_path, verbose=False)
    coverage = coverage_df.copy() if coverage_df is not None else pd.DataFrame()
    useful_pct = float(coverage.get("coverage_pct", pd.Series(dtype=float)).mean()) if not coverage.empty else 0.0
    if coverage.empty:
        status = "COVERAGE_INSUFFICIENT"
    elif "requirements_status" in coverage.columns and (coverage["requirements_status"].astype(str).str.endswith("FAIL") | coverage["requirements_status"].astype(str).eq("COVERAGE_INSUFFICIENT")).any():
        status = "COVERAGE_INSUFFICIENT"
    elif useful_pct >= 0.5:
        status = "COVERAGE_REQUIREMENTS_PASS"
    else:
        status = "COVERAGE_REQUIREMENTS_WARNING"
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO signal_coverage_runs (
                created_at, start_date, end_date, sources_checked, coverage_status,
                useful_cells_pct, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(timespec="seconds"),
                start_date,
                end_date,
                ",".join(sources_checked or coverage.get("signal_source", pd.Series(dtype=str)).astype(str).tolist()),
                status,
                round(useful_pct, 6),
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
            ),
        )
        run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        if not coverage.empty:
            out = coverage.copy()
            out["run_id"] = run_id
            out["metadata_json"] = out.apply(lambda r: json.dumps({"first_signal_date": r.get("first_signal_date"), "latest_signal_date": r.get("latest_signal_date"), "requirements_message": r.get("requirements_message")}, ensure_ascii=False, default=str), axis=1)
            cols = [c for c in SOURCE_COLUMNS if c != "id"]
            for col in cols:
                if col not in out.columns:
                    out[col] = pd.NA
            out[cols].to_sql("signal_coverage_by_source", con, if_exists="append", index=False)
        con.commit()
    return run_id


def _read(db_path: str | Path, sql: str, params=None, columns=None) -> pd.DataFrame:
    columns = columns or []
    if not Path(db_path).exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            return pd.read_sql_query(sql, con, params=params or [])
    except sqlite3.Error:
        return pd.DataFrame(columns=columns)


def load_latest_signal_coverage(db_path: str | Path) -> pd.DataFrame:
    run = _read(db_path, "SELECT id FROM signal_coverage_runs ORDER BY id DESC LIMIT 1", columns=["id"])
    if run.empty:
        return pd.DataFrame(columns=SOURCE_COLUMNS)
    return _read(db_path, "SELECT * FROM signal_coverage_by_source WHERE run_id = ? ORDER BY signal_source", [int(run.iloc[0]["id"])], SOURCE_COLUMNS)


def load_signal_coverage_history(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read(db_path, f"SELECT * FROM signal_coverage_runs ORDER BY id DESC LIMIT {int(limit)}", columns=RUN_COLUMNS)

