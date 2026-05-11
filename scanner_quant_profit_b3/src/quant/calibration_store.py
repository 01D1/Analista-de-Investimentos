"""Persistência do histórico de calibração do score quantitativo."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def _get(row: pd.Series, key: str, default: Any = None) -> Any:
    return row[key] if key in row.index else default


def save_calibration_run(
    df_comparison: pd.DataFrame,
    distribution_stats: dict,
    inflation_alert: dict,
    db_path: str | Path,
    source: str = "realtime",
) -> int:
    db_path = Path(db_path)
    init_database(db_path, verbose=False)

    dist = distribution_stats or {}
    inflation = inflation_alert or dist.get("inflation_alert", {})
    percentiles = dist.get("percentiles", {})
    buckets = dist.get("buckets", {})

    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO score_calibration_runs (
                created_at, source, total_assets,
                mean_score_final, median_score_final, std_score_final,
                min_score_final, max_score_final,
                p10_score_final, p25_score_final, p50_score_final,
                p75_score_final, p90_score_final,
                count_0_20, count_20_40, count_40_60, count_60_80, count_80_100,
                inflation_alert, inflation_message, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                source,
                int(dist.get("count", len(df_comparison) if df_comparison is not None else 0)),
                dist.get("mean"),
                dist.get("median"),
                dist.get("std"),
                dist.get("min"),
                dist.get("max"),
                percentiles.get("p10"),
                percentiles.get("p25"),
                percentiles.get("p50"),
                percentiles.get("p75"),
                percentiles.get("p90"),
                buckets.get("0_20"),
                buckets.get("20_40"),
                buckets.get("40_60"),
                buckets.get("60_80"),
                buckets.get("80_100"),
                1 if inflation.get("has_alert") else 0,
                inflation.get("message"),
                _json({"distribution": dist, "inflation": inflation}),
            ),
        )
        run_id = int(cur.lastrowid)

        if df_comparison is not None and not df_comparison.empty:
            for _, row in df_comparison.iterrows():
                metadata = {
                    "score_diff": _get(row, "score_diff"),
                    "score_diff_abs": _get(row, "score_diff_abs"),
                    "score_diff_pct": _get(row, "score_diff_pct"),
                    "legacy_signal_family": _get(row, "legacy_signal_family"),
                    "new_signal_family": _get(row, "new_signal_family"),
                    "signal_divergence": _get(row, "signal_divergence"),
                }
                cur.execute(
                    """
                    INSERT INTO score_calibration_assets (
                        run_id, captured_at, asset, legacy_score, score_final,
                        score_momentum, score_tendencia, score_liquidez,
                        score_volatilidade, score_risco, legacy_signal, signal_type,
                        signal_confidence, divergence_type, ranking_legacy,
                        ranking_new, ranking_change, explanation, metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_id,
                        _get(row, "captured_at"),
                        _get(row, "asset"),
                        _get(row, "score"),
                        _get(row, "score_final"),
                        _get(row, "score_momentum"),
                        _get(row, "score_tendencia"),
                        _get(row, "score_liquidez"),
                        _get(row, "score_volatilidade"),
                        _get(row, "score_risco"),
                        _get(row, "signal", ""),
                        _get(row, "signal_type"),
                        _get(row, "signal_confidence"),
                        _get(row, "divergence_type"),
                        _get(row, "legacy_rank"),
                        _get(row, "new_rank"),
                        _get(row, "rank_change"),
                        _get(row, "explanation"),
                        _json(metadata),
                    ),
                )
        con.commit()

    return run_id


def load_calibration_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query(
            "SELECT * FROM score_calibration_runs ORDER BY id DESC LIMIT ?",
            con,
            params=(limit,),
        )


def load_calibration_assets(db_path: str | Path, run_id: int) -> pd.DataFrame:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query(
            "SELECT * FROM score_calibration_assets WHERE run_id = ? ORDER BY ranking_new, id",
            con,
            params=(run_id,),
        )


def get_score_distribution_history(db_path: str | Path) -> pd.DataFrame:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        return pd.read_sql_query(
            """
            SELECT id, created_at, source, total_assets, mean_score_final,
                   median_score_final, std_score_final, min_score_final,
                   max_score_final, p10_score_final, p25_score_final,
                   p50_score_final, p75_score_final, p90_score_final,
                   count_0_20, count_20_40, count_40_60, count_60_80,
                   count_80_100, inflation_alert, inflation_message
            FROM score_calibration_runs
            ORDER BY id
            """,
            con,
        )
