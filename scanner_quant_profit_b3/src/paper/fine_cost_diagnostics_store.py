"""Persistencia do diagnostico fino de custos do paper trading."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database


ORDER_REASON_COLUMNS = [
    "id",
    "run_id",
    "order_id",
    "ticker",
    "trade_date",
    "original_reason",
    "normalized_order_reason",
    "reason_confidence",
    "is_unknown",
    "missing_metadata_fields_json",
    "metadata_json",
]

LIFECYCLE_COLUMNS = [
    "id",
    "run_id",
    "lifecycle_id",
    "ticker",
    "entry_date",
    "exit_date",
    "holding_days",
    "entry_cost",
    "exit_cost",
    "rebalance_cost",
    "total_cost",
    "total_slippage",
    "gross_pnl",
    "net_pnl",
    "cost_to_pnl_ratio",
    "metadata_json",
]

REBALANCE_COLUMNS = [
    "id",
    "run_id",
    "ticker",
    "rebalance_cost_total",
    "rebalance_slippage_total",
    "rebalance_orders_count",
    "rebalance_cost_class",
    "metadata_json",
]

EXIT_RULE_COLUMNS = [
    "id",
    "run_id",
    "exit_rule",
    "exit_count",
    "gross_pnl",
    "net_pnl",
    "transaction_cost",
    "slippage_cost",
    "cost_drag",
    "cost_to_pnl_ratio",
    "exit_rule_cost_class",
    "metadata_json",
]

UNKNOWN_COLUMNS = [
    "id",
    "run_id",
    "unknown_orders_count",
    "unknown_cost_total",
    "unknown_slippage_total",
    "missing_fields_summary_json",
    "required_metadata_fixes_json",
    "metadata_json",
]


def _prepare(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col != "id" and col not in out.columns:
            out[col] = pd.NA
    return out[[c for c in columns if c != "id"]]


def save_fine_cost_diagnostics(
    db_path: str | Path,
    run_id: int,
    order_reasons_df: pd.DataFrame | None = None,
    lifecycle_df: pd.DataFrame | None = None,
    rebalance_df: pd.DataFrame | None = None,
    exit_rule_df: pd.DataFrame | None = None,
    unknown_summary: dict | None = None,
) -> int:
    """Salvar diagnostico fino usando o paper_run_id como run_id analitico."""
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        if order_reasons_df is not None and not order_reasons_df.empty:
            order_df = order_reasons_df.copy()
            order_df["run_id"] = int(run_id)
            order_df["order_id"] = order_df.get("id", order_df.index).astype(str)
            order_df["original_reason"] = order_df.get("signal_source", pd.Series("", index=order_df.index)).astype(str)
            _prepare(order_df, ORDER_REASON_COLUMNS).to_sql("paper_order_reason_diagnostics", con, if_exists="append", index=False)
        if lifecycle_df is not None and not lifecycle_df.empty:
            life = lifecycle_df.copy()
            life["run_id"] = int(run_id)
            _prepare(life, LIFECYCLE_COLUMNS).to_sql("paper_cost_lifecycle", con, if_exists="append", index=False)
        if rebalance_df is not None and not rebalance_df.empty:
            reb = rebalance_df.copy()
            reb["run_id"] = int(run_id)
            if "rebalance_cost_class" not in reb.columns:
                reb["rebalance_cost_class"] = reb.get("metadata_json", "{}").map(lambda _: "REBALANCE_COST_OK")
            _prepare(reb, REBALANCE_COLUMNS).to_sql("paper_rebalance_cost_diagnostics", con, if_exists="append", index=False)
        if exit_rule_df is not None and not exit_rule_df.empty:
            exit_df = exit_rule_df.copy()
            exit_df["run_id"] = int(run_id)
            _prepare(exit_df, EXIT_RULE_COLUMNS).to_sql("paper_exit_rule_cost_diagnostics", con, if_exists="append", index=False)
        if unknown_summary is not None:
            unk = dict(unknown_summary)
            unk["run_id"] = int(run_id)
            if isinstance(unk.get("missing_fields_summary"), dict):
                unk["missing_fields_summary_json"] = json.dumps(unk["missing_fields_summary"], ensure_ascii=False)
            if isinstance(unk.get("required_metadata_fixes"), list):
                unk["required_metadata_fixes_json"] = json.dumps(unk["required_metadata_fixes"], ensure_ascii=False)
            _prepare(pd.DataFrame([unk]), UNKNOWN_COLUMNS).to_sql("paper_unknown_cost_diagnostics", con, if_exists="append", index=False)
    return int(run_id)


def _read(db_path: str | Path, table: str, columns: list[str], run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame(columns=columns)
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return pd.DataFrame(columns=columns)
            sql = f"SELECT * FROM {table}"
            params = []
            if run_id is not None:
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


def load_fine_cost_diagnostics(db_path: str | Path, run_id: int | None = None) -> dict:
    return {
        "order_reasons": load_order_reason_diagnostics(db_path, run_id=run_id),
        "lifecycle": load_lifecycle_costs(db_path, run_id=run_id),
        "rebalance": load_rebalance_cost_diagnostics(db_path, run_id=run_id),
        "exit_rules": load_exit_rule_cost_diagnostics(db_path, run_id=run_id),
        "unknown": load_unknown_cost_diagnostics(db_path, run_id=run_id),
    }


def load_order_reason_diagnostics(db_path: str | Path, run_id: int | None = None, limit: int = 5000) -> pd.DataFrame:
    return _read(db_path, "paper_order_reason_diagnostics", ORDER_REASON_COLUMNS, run_id=run_id, limit=limit)


def load_lifecycle_costs(db_path: str | Path, run_id: int | None = None, limit: int = 5000) -> pd.DataFrame:
    return _read(db_path, "paper_cost_lifecycle", LIFECYCLE_COLUMNS, run_id=run_id, limit=limit)


def load_rebalance_cost_diagnostics(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_rebalance_cost_diagnostics", REBALANCE_COLUMNS, run_id=run_id, limit=limit)


def load_exit_rule_cost_diagnostics(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_exit_rule_cost_diagnostics", EXIT_RULE_COLUMNS, run_id=run_id, limit=limit)


def load_unknown_cost_diagnostics(db_path: str | Path, run_id: int | None = None, limit: int = 1000) -> pd.DataFrame:
    return _read(db_path, "paper_unknown_cost_diagnostics", UNKNOWN_COLUMNS, run_id=run_id, limit=limit)
