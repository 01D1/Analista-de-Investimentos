"""Persistencia de manifestos de arquivos."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.file_manifest import FILE_MANIFEST_COLUMNS
from src.db.init_db import init_database


def save_file_manifest_run(db_path: str | Path, manifest_df: pd.DataFrame, comparison_df: pd.DataFrame | None = None) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)
    now = datetime.now().isoformat(timespec="seconds")
    files_count = int(len(manifest_df) if manifest_df is not None else 0)
    comparison = comparison_df if comparison_df is not None else pd.DataFrame()
    new_count = int((comparison.get("change_type", pd.Series(dtype=str)) == "NEW_FILE").sum()) if not comparison.empty else files_count
    changed_count = int((comparison.get("change_type", pd.Series(dtype=str)) == "CHANGED_FILE").sum()) if not comparison.empty else 0
    removed_count = int((comparison.get("change_type", pd.Series(dtype=str)) == "REMOVED_FILE").sum()) if not comparison.empty else 0
    status = "OK" if changed_count == 0 and removed_count == 0 else "WARNING"
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO data_file_manifest_runs (
                started_at, finished_at, files_count, new_files_count,
                changed_files_count, removed_files_count, status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, now, files_count, new_count, changed_count, removed_count, status, json.dumps({"comparison_rows": len(comparison)}, ensure_ascii=False)),
        )
        run_id = int(cur.lastrowid)
        con.execute("UPDATE data_file_manifest SET active = 0 WHERE active = 1")
        if manifest_df is not None and not manifest_df.empty:
            rows = []
            for _, row in manifest_df.iterrows():
                rows.append(
                    (
                        now,
                        row.get("file_path"),
                        row.get("file_name"),
                        row.get("extension"),
                        int(row.get("size_bytes") or 0),
                        row.get("modified_at"),
                        row.get("checksum"),
                        row.get("source_domain"),
                        1,
                        row.get("metadata_json"),
                    )
                )
            con.executemany(
                """
                INSERT INTO data_file_manifest (
                    created_at, file_path, file_name, extension, size_bytes, modified_at,
                    checksum, source_domain, active, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        con.commit()
    return run_id


def load_latest_file_manifest(db_path: str | Path) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame(columns=FILE_MANIFEST_COLUMNS)
    try:
        with sqlite3.connect(db_path) as con:
            return pd.read_sql_query(
                """
                SELECT file_path, file_name, extension, size_bytes, modified_at,
                       checksum, source_domain, metadata_json
                FROM data_file_manifest
                WHERE active = 1
                ORDER BY file_path
                """,
                con,
            )
    except Exception:
        return pd.DataFrame(columns=FILE_MANIFEST_COLUMNS)


def load_file_manifest_history(db_path: str | Path, file_path: str | None = None, limit: int = 1000) -> pd.DataFrame:
    db_path = Path(db_path)
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            sql = "SELECT * FROM data_file_manifest"
            params: list = []
            if file_path:
                sql += " WHERE file_path = ?"
                params.append(file_path)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(int(limit))
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()

