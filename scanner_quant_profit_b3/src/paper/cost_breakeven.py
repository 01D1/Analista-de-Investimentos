"""Análise de break-even de custo e slippage."""
from __future__ import annotations

import pandas as pd


def calculate_cost_breakeven(results_df: pd.DataFrame) -> dict:
    if results_df is None or results_df.empty:
        return {
            "max_cost_bps_supported": 0.0,
            "max_slippage_bps_supported": 0.0,
            "breakeven_turnover_reduction": 0.0,
            "breakeven_trade_return_required": 0.0,
            "negative_return_scenario": "INSUFFICIENT_DATA",
            "metadata_json": "{}",
        }
    df = results_df.copy()
    return_col = "total_return" if "total_return" in df.columns else "mean_return" if "mean_return" in df.columns else "mean_return_delta" if "mean_return_delta" in df.columns else ""
    if not return_col:
        return calculate_cost_breakeven(pd.DataFrame())
    df["_return"] = pd.to_numeric(df[return_col], errors="coerce").fillna(0)
    df["cost_bps"] = pd.to_numeric(df["cost_bps"] if "cost_bps" in df.columns else 10, errors="coerce").fillna(10)
    df["slippage_bps"] = pd.to_numeric(df["slippage_bps"] if "slippage_bps" in df.columns else 5, errors="coerce").fillna(5)
    df["trades_count"] = pd.to_numeric(df["trades_count"] if "trades_count" in df.columns else 1, errors="coerce").fillna(1)
    positive = df[df["_return"] >= 0]
    negative = df[df["_return"] < 0].sort_values(["cost_bps", "slippage_bps"]).head(1)
    max_cost = float(positive["cost_bps"].max()) if not positive.empty else 0.0
    max_slip = float(positive["slippage_bps"].max()) if not positive.empty else 0.0
    base = df.sort_values(["cost_bps", "slippage_bps"]).head(1).iloc[0]
    avg_trade_return = float(base["_return"] / max(float(base["trades_count"]), 1.0))
    total_bps = float(base["cost_bps"] + base["slippage_bps"]) / 10000
    required = max(0.0, total_bps - avg_trade_return)
    worst_neg = float(negative.iloc[0]["_return"]) if not negative.empty else 0.0
    turnover_reduction = min(1.0, abs(worst_neg) / max(abs(float(df["_return"].mean())) + abs(worst_neg), 1e-9)) if not negative.empty else 0.0
    neg_name = str(negative.iloc[0].get("scenario_name", negative.iloc[0].get("cost_scenario", "NEGATIVE_RETURN"))) if not negative.empty else "NO_NEGATIVE_SCENARIO"
    return {
        "max_cost_bps_supported": round(max_cost, 6),
        "max_slippage_bps_supported": round(max_slip, 6),
        "breakeven_turnover_reduction": round(float(turnover_reduction), 6),
        "breakeven_trade_return_required": round(float(required), 6),
        "negative_return_scenario": neg_name,
        "metadata_json": "{}",
    }
