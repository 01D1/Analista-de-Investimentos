"""Governança das variações LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import pandas as pd


def _f(row, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def evaluate_limit_signal_source_variant(row) -> str:
    if bool(row.get("low_sample_flag", False)) or _f(row, "trades_count") < 20:
        return "LIMIT_SOURCE_BLOCKED_LOW_SAMPLE"
    if bool(row.get("overfitting_flag", False)) or _f(row, "removed_pct") > 0.75:
        return "LIMIT_SOURCE_BLOCKED_OVERFITTING"
    if bool(row.get("cost_sensitivity_flag", False)) or _f(row, "mean_cost_drag_delta") > 0:
        return "LIMIT_SOURCE_BLOCKED_COST"
    if bool(row.get("slippage_sensitivity_flag", False)) or _f(row, "mean_slippage_delta") > 0:
        return "LIMIT_SOURCE_BLOCKED_SLIPPAGE"
    if _f(row, "mean_return_delta") < 0:
        return "LIMIT_SOURCE_BLOCKED_RETURN_DEGRADATION"
    if _f(row, "positive_improvement_pct") >= 0.60 and _f(row, "mean_fragility_delta") < 0 and _f(row, "mean_drawdown_delta") >= -0.001:
        return "LIMIT_SOURCE_APPROVED_FOR_OBSERVATION"
    if _f(row, "positive_improvement_pct") >= 0.45 and _f(row, "mean_fragility_delta") < 0:
        return "LIMIT_SOURCE_MORE_TESTING_REQUIRED"
    return "LIMIT_SOURCE_REJECTED"

