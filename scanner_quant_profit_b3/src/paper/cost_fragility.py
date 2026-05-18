"""Sensibilidade a custos e slippage por ativo/cenario."""
from __future__ import annotations

import pandas as pd

from src.paper.fragility_by_asset import _extract_pnl


def _classify(row) -> str:
    pnl = float(row.get("net_pnl", row.get("mean_return", 0)) or 0)
    ratio = float(row.get("cost_to_pnl_ratio", 0) or 0)
    if ratio < 0.25 and pnl > 0:
        return "COST_ROBUST"
    if ratio < 0.75 and pnl > 0:
        return "COST_SENSITIVE"
    if pnl <= 0:
        return "COST_FRAGILE"
    return "COST_DOMINATED"


def analyze_cost_drag_by_asset(orders_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["ticker", "transaction_cost_total", "slippage_cost_total", "cost_drag_pct", "slippage_drag_pct", "cost_to_pnl_ratio", "cost_fragility_class", "metadata_json"]
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(columns=columns)
    work = orders_df.copy()
    work["ticker"] = work["ticker"].astype(str).str.upper()
    work["trade_pnl"] = work.apply(_extract_pnl, axis=1)
    work["execution_cost"] = pd.to_numeric(work.get("execution_cost"), errors="coerce").fillna(0)
    work["slippage_cost"] = pd.to_numeric(work.get("slippage_cost"), errors="coerce").fillna(0)
    rows = []
    for ticker, group in work.groupby("ticker"):
        pnl = float(group["trade_pnl"].sum())
        tx = float(group["execution_cost"].sum())
        sl = float(group["slippage_cost"].sum())
        denom = max(abs(pnl) + tx + sl, 1.0)
        row = {
            "ticker": ticker,
            "transaction_cost_total": round(tx, 6),
            "slippage_cost_total": round(sl, 6),
            "cost_drag_pct": round(float(tx / denom), 6),
            "slippage_drag_pct": round(float(sl / denom), 6),
            "cost_to_pnl_ratio": round(float((tx + sl) / max(abs(pnl), 1.0)), 6),
            "net_pnl": pnl,
            "metadata_json": "{}",
        }
        row["cost_fragility_class"] = _classify(row)
        rows.append(row)
    return pd.DataFrame(rows)[columns]


def analyze_cost_drag_by_scenario(scenario_results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["scenario_id", "scenario_name", "signal_source", "cost_bps", "slippage_bps", "mean_return", "positive_periods_pct", "cost_fragility_class", "metadata_json"]
    if scenario_results_df is None or scenario_results_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for keys, group in scenario_results_df.groupby(["scenario_id", "scenario_name", "signal_source", "cost_bps", "slippage_bps"], dropna=False):
        ret = pd.to_numeric(group["total_return"], errors="coerce").fillna(0)
        row = {
            "scenario_id": keys[0],
            "scenario_name": keys[1],
            "signal_source": keys[2],
            "cost_bps": float(keys[3]),
            "slippage_bps": float(keys[4]),
            "mean_return": round(float(ret.mean()), 6),
            "positive_periods_pct": round(float((ret > 0).mean()), 4),
            "metadata_json": "{}",
        }
        row["cost_fragility_class"] = "COST_ROBUST" if row["mean_return"] > 0 and row["positive_periods_pct"] >= 0.5 else "COST_FRAGILE"
        rows.append(row)
    return pd.DataFrame(rows)[columns]
