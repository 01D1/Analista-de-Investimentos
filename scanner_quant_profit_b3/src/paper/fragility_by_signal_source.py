"""Diagnostico de fragilidade por fonte de sinal."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.fragility_by_asset import _extract_pnl
from src.paper.fragility_score import add_fragility_columns


def _metadata_value(row, key: str, fallback="-"):
    try:
        meta = json.loads(row.get("metadata_json") or "{}")
        return meta.get(key, fallback)
    except (TypeError, json.JSONDecodeError):
        return fallback


def analyze_pnl_by_signal_source(orders_df: pd.DataFrame, positions_df: pd.DataFrame | None = None) -> pd.DataFrame:
    columns = ["signal_source", "setup_type", "quant_signal_type", "technical_setup", "integrated_status", "trades", "net_pnl", "contribution_pct", "win_rate", "avg_return", "drawdown_contribution", "turnover", "cost_drag", "fragility_score", "fragility_class", "metadata_json"]
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(columns=columns)
    work = orders_df.copy()
    status = work.get("order_status", work.get("status", pd.Series(dtype=str))).astype(str)
    work = work[status == "SIMULATED_FILLED"].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["trade_pnl"] = work.apply(_extract_pnl, axis=1)
    work["cost_drag"] = pd.to_numeric(work.get("execution_cost"), errors="coerce").fillna(0) + pd.to_numeric(work.get("slippage_cost"), errors="coerce").fillna(0)
    for col in ["setup_type", "quant_signal_type", "technical_setup", "integrated_status"]:
        work[col] = work.apply(lambda row: _metadata_value(row, col), axis=1)
    work["signal_source"] = work.get("signal_source", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str)
    total_abs = max(float(work["trade_pnl"].abs().sum()), 1.0)
    rows = []
    for keys, group in work.groupby(["signal_source", "setup_type", "quant_signal_type", "technical_setup", "integrated_status"], dropna=False):
        pnl = pd.to_numeric(group["trade_pnl"], errors="coerce").fillna(0)
        net = float(pnl.sum())
        rows.append(
            {
                "signal_source": keys[0],
                "setup_type": keys[1],
                "quant_signal_type": keys[2],
                "technical_setup": keys[3],
                "integrated_status": keys[4],
                "trades": int(len(group)),
                "net_pnl": round(net, 6),
                "contribution_pct": round(float(net / total_abs), 6),
                "win_rate": round(float((pnl > 0).mean()), 6),
                "avg_return": round(float(pnl.mean()), 6),
                "drawdown_contribution": round(abs(float(pnl.min())), 6),
                "turnover": int(len(group)),
                "cost_drag": round(float(group["cost_drag"].sum()), 6),
                "metadata_json": "{}",
            }
        )
    return add_fragility_columns(pd.DataFrame(rows))[columns]
