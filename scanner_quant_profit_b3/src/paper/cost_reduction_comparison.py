"""Comparacao baseline vs variante simulada de reducao de custos."""
from __future__ import annotations

import pandas as pd


def _first(df: pd.DataFrame | dict) -> dict:
    if isinstance(df, dict):
        return dict(df)
    if df is None or df.empty:
        return {}
    return df.iloc[0].to_dict()


def compare_cost_variant_to_baseline(baseline_df: pd.DataFrame | dict, variant_df: pd.DataFrame | dict) -> dict:
    """Comparar métricas de uma variante contra baseline da própria simulação."""
    base = _first(baseline_df)
    var = _first(variant_df)
    if not base or not var:
        return {
            "return_delta": 0.0,
            "drawdown_delta": 0.0,
            "cost_drag_delta": 0.0,
            "exit_cost_delta": 0.0,
            "rebalance_cost_delta": 0.0,
            "turnover_delta": 0.0,
            "trades_delta": 0.0,
            "profit_factor_delta": 0.0,
            "improvement_score": 0.0,
            "comparison_class": "COST_VARIANT_INSUFFICIENT_DATA",
        }
    return_delta = float(var.get("total_return", 0) or 0) - float(base.get("total_return", 0) or 0)
    drawdown_delta = float(var.get("max_drawdown", 0) or 0) - float(base.get("max_drawdown", 0) or 0)
    cost_drag_delta = float(var.get("cost_drag_total", 0) or 0) - float(base.get("cost_drag_total", 0) or 0)
    exit_cost_delta = float(var.get("exit_cost", 0) or 0) - float(base.get("exit_cost", 0) or 0)
    rebalance_cost_delta = float(var.get("rebalance_cost", 0) or 0) - float(base.get("rebalance_cost", 0) or 0)
    turnover_delta = float(var.get("turnover", 0) or 0) - float(base.get("turnover", 0) or 0)
    trades_delta = float(var.get("trades_count", 0) or 0) - float(base.get("trades_count", 0) or 0)
    profit_factor_delta = float(var.get("profit_factor", 0) or 0) - float(base.get("profit_factor", 0) or 0)
    cost_reduction = -cost_drag_delta
    base_cost = max(float(base.get("cost_drag_total", 0) or 0), 1.0)
    score = 50 * max(min(cost_reduction / base_cost, 1), -1) + 25 * max(min(return_delta / 0.02, 1), -1) + 15 * (1 if drawdown_delta >= 0 else -1) + 10 * max(min(profit_factor_delta, 1), -1)
    score = round(float(max(0, min(100, 50 + score))), 6)
    if cost_reduction > 0 and return_delta >= -0.002 and drawdown_delta >= -0.01:
        klass = "COST_VARIANT_IMPROVED"
    elif cost_reduction > 0 and (return_delta < 0 or drawdown_delta < 0):
        klass = "COST_VARIANT_MIXED"
    elif cost_reduction <= 0 and return_delta >= 0:
        klass = "COST_VARIANT_NO_IMPROVEMENT"
    else:
        klass = "COST_VARIANT_WORSE"
    return {
        "return_delta": round(return_delta, 6),
        "drawdown_delta": round(drawdown_delta, 6),
        "cost_drag_delta": round(cost_drag_delta, 6),
        "exit_cost_delta": round(exit_cost_delta, 6),
        "rebalance_cost_delta": round(rebalance_cost_delta, 6),
        "turnover_delta": round(turnover_delta, 6),
        "trades_delta": round(trades_delta, 6),
        "profit_factor_delta": round(profit_factor_delta, 6),
        "improvement_score": score,
        "comparison_class": klass,
    }
