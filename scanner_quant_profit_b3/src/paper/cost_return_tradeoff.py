"""Metricas de trade-off entre custo, retorno e drawdown."""
from __future__ import annotations

import json

import pandas as pd


def _num(series, default=0.0) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _tradeoff_class(row) -> str:
    cost = float(row.get("cost_reduction_pct", 0) or 0)
    ret = float(row.get("return_delta", 0) or 0)
    dd = float(row.get("drawdown_delta", 0) or 0)
    trades = float(row.get("trades_count", 0) or 0)
    if trades <= 0:
        return "INSUFFICIENT_DATA"
    if cost > 0 and ret >= 0 and dd >= 0:
        return "EFFICIENT_TRADEOFF"
    if cost > 0 and ret >= -0.005 and dd >= -0.01:
        return "ACCEPTABLE_TRADEOFF"
    if cost > 0 and (ret > -0.02 or dd > -0.03):
        return "MIXED_TRADEOFF"
    return "BAD_TRADEOFF"


def calculate_tradeoff_metrics(variants_df: pd.DataFrame) -> pd.DataFrame:
    """Calcular métricas de trade-off para variantes em estudo."""
    columns = [
        "variant_id",
        "variant_type",
        "cost_reduction_pct",
        "return_delta",
        "drawdown_delta",
        "turnover_delta",
        "trades_delta",
        "profit_factor_delta",
        "cost_reduction_to_return_loss",
        "cost_reduction_to_drawdown_penalty",
        "efficiency_score",
        "tradeoff_class",
        "metadata_json",
    ]
    if variants_df is None or variants_df.empty:
        return pd.DataFrame(columns=columns)
    out = variants_df.copy()
    out["cost_reduction_pct"] = _num(out.get("cost_reduction_pct"), 0.0)
    out["return_delta"] = _num(out.get("return_delta"), 0.0)
    out["drawdown_delta"] = _num(out.get("drawdown_delta"), 0.0)
    out["turnover_delta"] = _num(out.get("turnover_delta"), 0.0)
    out["trades_delta"] = _num(out.get("trades_delta"), 0.0)
    out["profit_factor_delta"] = _num(out.get("profit_factor_delta"), 0.0)
    return_loss = (-out["return_delta"]).clip(lower=0)
    drawdown_penalty = (-out["drawdown_delta"]).clip(lower=0)
    out["cost_reduction_to_return_loss"] = out["cost_reduction_pct"] / return_loss.replace(0, 0.001)
    out["cost_reduction_to_drawdown_penalty"] = out["cost_reduction_pct"] / drawdown_penalty.replace(0, 0.001)
    out["efficiency_score"] = (
        50 * out["cost_reduction_pct"].clip(lower=-1, upper=1)
        + 25 * (out["return_delta"] / 0.02).clip(lower=-1, upper=1)
        + 20 * (out["drawdown_delta"] / 0.02).clip(lower=-1, upper=1)
        + 5 * (-out["turnover_delta"] / out["turnover_delta"].abs().replace(0, 1).max()).clip(lower=-1, upper=1)
        + 50
    ).clip(lower=0, upper=100).round(6)
    out["tradeoff_class"] = out.apply(_tradeoff_class, axis=1)
    out["metadata_json"] = out.get("metadata_json", pd.Series("{}", index=out.index)).fillna("{}")
    out["metadata_json"] = out.apply(
        lambda r: json.dumps({"tradeoff_class": r["tradeoff_class"], "variant_in_study": True, "nao_recomendacao": True}, ensure_ascii=False),
        axis=1,
    )
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns + [c for c in out.columns if c not in columns]]
