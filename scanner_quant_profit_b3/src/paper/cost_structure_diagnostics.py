"""Diagnóstico estrutural de custo e slippage no paper trading."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


def _num(series, default: float = 0.0) -> pd.Series:
    converted = pd.to_numeric(series, errors="coerce")
    if isinstance(converted, pd.Series):
        return converted.fillna(default)
    return pd.Series([converted]).fillna(default)


def _metadata(row: pd.Series) -> dict[str, Any]:
    raw = row.get("metadata_json")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _meta_value(row: pd.Series, *keys: str, default=None):
    meta = _metadata(row)
    for key in keys:
        if key in row and pd.notna(row.get(key)):
            return row.get(key)
        if key in meta:
            return meta.get(key)
    return default


def _prepare_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    work = orders_df.copy()
    for col in ["execution_cost", "slippage_cost", "quantity", "theoretical_price", "simulated_execution_price"]:
        work[col] = _num(work[col] if col in work.columns else pd.Series(0, index=work.index))
    if "ticker" in work.columns:
        work["ticker"] = work["ticker"].astype(str).str.upper()
    else:
        work["ticker"] = "UNKNOWN"
    work["signal_source"] = work.get("signal_source", "UNKNOWN").fillna("UNKNOWN").astype(str).str.lower()
    work["exit_reason"] = work.apply(lambda r: _meta_value(r, "exit_reason", "exit_rule_triggered", default="UNKNOWN"), axis=1).fillna("UNKNOWN").astype(str)
    work["regime"] = work.apply(lambda r: _meta_value(r, "primary_regime", "regime", "market_regime", default="SEM_REGIME"), axis=1).fillna("SEM_REGIME").astype(str)
    work["holding_period"] = pd.to_numeric(work.apply(lambda r: _meta_value(r, "holding_period", "holding_days", default=0), axis=1), errors="coerce").fillna(0)
    work["net_pnl"] = pd.to_numeric(work.apply(lambda r: _meta_value(r, "metadata_trade_pnl", "trade_pnl", "net_pnl", default=0), axis=1), errors="coerce").fillna(0)
    work["gross_pnl"] = pd.to_numeric(work.apply(lambda r: _meta_value(r, "gross_pnl", "metadata_gross_pnl", default=None), axis=1), errors="coerce")
    work["gross_pnl"] = work["gross_pnl"].fillna(work["net_pnl"] + work["execution_cost"] + work["slippage_cost"])
    work["total_cost_drag"] = work["execution_cost"] + work["slippage_cost"]
    return work


def classify_cost_drag(cost_drag_pct_of_gross_pnl: float | None, total_trades: int = 0) -> str:
    if not total_trades:
        return "INSUFFICIENT_DATA"
    ratio = float(cost_drag_pct_of_gross_pnl or 0)
    if ratio < 0.10:
        return "COST_DRAG_LOW"
    if ratio < 0.25:
        return "COST_DRAG_ACCEPTABLE"
    if ratio < 0.50:
        return "COST_DRAG_HIGH"
    return "COST_DRAG_DOMINATES_EDGE"


def _group_costs(work: pd.DataFrame, group_col: str) -> pd.DataFrame:
    columns = [group_col, "trades_count", "gross_pnl", "transaction_cost", "slippage_cost", "total_cost_drag", "cost_drag_pct", "cost_drag_class", "metadata_json"]
    if work.empty or group_col not in work.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for key, group in work.groupby(group_col, dropna=False, observed=False):
        gross = float(group["gross_pnl"].sum())
        tx = float(group["execution_cost"].sum())
        slip = float(group["slippage_cost"].sum())
        drag = tx + slip
        ratio = drag / max(abs(gross), 1.0)
        rows.append(
            {
                group_col: key,
                "trades_count": int(len(group)),
                "gross_pnl": round(gross, 6),
                "transaction_cost": round(tx, 6),
                "slippage_cost": round(slip, 6),
                "total_cost_drag": round(drag, 6),
                "cost_drag_pct": round(float(ratio), 6),
                "cost_drag_class": classify_cost_drag(ratio, len(group)),
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("total_cost_drag", ascending=False).reset_index(drop=True)


def analyze_cost_structure(orders_df: pd.DataFrame, positions_df: pd.DataFrame | None = None) -> dict[str, Any]:
    if orders_df is None or orders_df.empty:
        empty = pd.DataFrame()
        return {
            "summary": {
                "total_transaction_cost": 0.0,
                "total_slippage_cost": 0.0,
                "total_cost_drag": 0.0,
                "cost_drag_pct_of_gross_pnl": 0.0,
                "slippage_pct_of_gross_pnl": 0.0,
                "avg_cost_per_trade": 0.0,
                "avg_slippage_per_trade": 0.0,
                "cost_drag_class": "INSUFFICIENT_DATA",
                "metadata_json": "{}",
            },
            "cost_by_ticker": empty,
            "cost_by_signal_source": empty,
            "cost_by_exit_reason": empty,
            "cost_by_regime": empty,
            "cost_by_holding_period": empty,
        }
    work = _prepare_orders(orders_df)
    trades = int(len(work))
    tx = float(work["execution_cost"].sum())
    slip = float(work["slippage_cost"].sum())
    drag = tx + slip
    gross = float(work["gross_pnl"].sum())
    cost_ratio = drag / max(abs(gross), 1.0)
    slippage_ratio = slip / max(abs(gross), 1.0)
    holding_bins = work.copy()
    holding_bins["holding_period_bucket"] = pd.cut(holding_bins["holding_period"], bins=[-1, 0, 2, 5, 10, 10**9], labels=["SEM_DADO", "1-2D", "3-5D", "6-10D", "10D+"])
    summary = {
        "total_transaction_cost": round(tx, 6),
        "total_slippage_cost": round(slip, 6),
        "total_cost_drag": round(drag, 6),
        "cost_drag_pct_of_gross_pnl": round(float(cost_ratio), 6),
        "slippage_pct_of_gross_pnl": round(float(slippage_ratio), 6),
        "avg_cost_per_trade": round(float(tx / trades), 6) if trades else 0.0,
        "avg_slippage_per_trade": round(float(slip / trades), 6) if trades else 0.0,
        "cost_drag_class": classify_cost_drag(cost_ratio, trades),
        "metadata_json": json.dumps({"gross_pnl": gross, "trades_count": trades}, ensure_ascii=False, default=str),
    }
    return {
        "summary": summary,
        "cost_by_ticker": _group_costs(work, "ticker"),
        "cost_by_signal_source": _group_costs(work, "signal_source"),
        "cost_by_exit_reason": _group_costs(work, "exit_reason"),
        "cost_by_regime": _group_costs(work, "regime"),
        "cost_by_holding_period": _group_costs(holding_bins, "holding_period_bucket").rename(columns={"holding_period_bucket": "holding_period"}),
    }
