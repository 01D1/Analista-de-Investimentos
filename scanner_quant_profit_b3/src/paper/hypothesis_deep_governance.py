"""Governanca profunda de hipoteses em estudo."""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def _get(summary, key: str, default=None):
    if isinstance(summary, Mapping):
        return summary.get(key, default)
    if isinstance(summary, pd.Series):
        return summary.get(key, default)
    return getattr(summary, key, default)


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_deep_hypothesis_governance(summary) -> str:
    """Avalia se a hipotese em estudo pode seguir apenas para observacao.

    A aprovacao nao recomenda compra/venda e nao aplica a hipotese
    automaticamente; ela apenas libera observacao analitica.
    """
    primary = str(_get(summary, "primary_block_reason", "") or "")
    if primary == "BLOCKED_BY_COST":
        return "HYPOTHESIS_DEEP_BLOCKED_COST"
    if primary == "BLOCKED_BY_SLIPPAGE":
        return "HYPOTHESIS_DEEP_BLOCKED_SLIPPAGE"
    if primary == "BLOCKED_BY_REGIME":
        return "HYPOTHESIS_DEEP_BLOCKED_REGIME"
    if primary == "BLOCKED_BY_SIGNAL_SOURCE":
        return "HYPOTHESIS_DEEP_BLOCKED_SOURCE"
    if primary == "BLOCKED_BY_ASSET_CONCENTRATION":
        return "HYPOTHESIS_DEEP_BLOCKED_ASSET"
    if primary == "BLOCKED_BY_OVERFITTING":
        return "HYPOTHESIS_DEEP_BLOCKED_OVERFITTING"

    positive = _as_float(_get(summary, "positive_improvement_pct"))
    ret = _as_float(_get(summary, "mean_return_delta"))
    drawdown = _as_float(_get(summary, "mean_drawdown_delta"))
    fragility = _as_float(_get(summary, "mean_fragility_delta"))
    useful_sources = int(_as_float(_get(summary, "useful_sources_count")))
    useful_regimes = int(_as_float(_get(summary, "useful_regimes_count")))
    asset_concentration = _as_float(_get(summary, "asset_concentration_pct"))
    cost_flag = bool(_get(summary, "cost_sensitivity_flag", False))
    slippage_flag = bool(_get(summary, "slippage_sensitivity_flag", False))
    overfit = bool(_get(summary, "overfitting_flag", False))

    if overfit:
        return "HYPOTHESIS_DEEP_BLOCKED_OVERFITTING"
    if cost_flag:
        return "HYPOTHESIS_DEEP_BLOCKED_COST"
    if slippage_flag:
        return "HYPOTHESIS_DEEP_BLOCKED_SLIPPAGE"
    if useful_sources < 2 or useful_regimes < 2:
        return "HYPOTHESIS_DEEP_MORE_TESTING_REQUIRED"
    if asset_concentration > 0.6:
        return "HYPOTHESIS_DEEP_BLOCKED_ASSET"
    if positive >= 0.6 and ret >= 0 and drawdown >= -0.001 and fragility < 0:
        return "HYPOTHESIS_DEEP_APPROVED_FOR_OBSERVATION"
    if ret < 0 and fragility >= 0:
        return "HYPOTHESIS_DEEP_REJECTED"
    return "HYPOTHESIS_DEEP_MORE_TESTING_REQUIRED"
