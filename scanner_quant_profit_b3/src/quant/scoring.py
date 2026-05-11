"""Score quantitativo composto para ativos."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from .metrics import to_float


DEFAULT_WEIGHTS = {
    "momentum": 0.35,
    "tendencia": 0.25,
    "liquidez": 0.20,
    "volatilidade": 0.10,
    "risco": 0.10,
}


def _clip(value: float) -> float:
    return round(float(np.clip(value, 0.0, 100.0)), 4)


def _score_momentum(metrics: Mapping[str, Any]) -> float:
    score = 0.0
    if to_float(metrics.get("variation_pct"), 0.0) > 0:
        score += 25
    if to_float(metrics.get("last_vs_open_pct"), 0.0) > 0:
        score += 20
    if to_float(metrics.get("last_vs_prev_close_pct"), 0.0) > 0:
        score += 20
    if to_float(metrics.get("position_range_pct"), 0.0) >= 75:
        score += 20
    if to_float(metrics.get("variation_pct"), 0.0) >= 1.5:
        score += 15
    return _clip(score)


def _score_trend(trend: Mapping[str, Any] | None) -> float:
    if not trend:
        return 50.0
    score = 0.0
    if trend.get("price_above_fast_ma"):
        score += 35
    if trend.get("price_above_slow_ma"):
        score += 35
    if trend.get("fast_ma_above_slow_ma"):
        score += 30
    return _clip(score)


def _score_volatility(metrics: Mapping[str, Any]) -> float:
    range_pct = to_float(metrics.get("range_pct"), 0.0)
    if range_pct <= 0:
        return 40.0
    if range_pct <= 2.0:
        return 55.0
    if range_pct <= 6.0:
        return 100.0
    if range_pct <= 9.0:
        return 75.0
    if range_pct <= 12.0:
        return 45.0
    return 20.0


def _score_risk(metrics: Mapping[str, Any], liquidity: Mapping[str, Any]) -> tuple[float, list[str]]:
    score = 100.0
    reasons: list[str] = []
    if to_float(metrics.get("gap_pct"), 0.0) >= 4.0:
        score -= 20
        reasons.append("gap elevado")
    if to_float(metrics.get("range_pct"), 0.0) >= 9.0:
        score -= 20
        reasons.append("range intradiário esticado")
    if to_float(metrics.get("position_range_pct"), 0.0) >= 95 and to_float(metrics.get("range_pct"), 0.0) >= 8.0:
        score -= 20
        reasons.append("preço muito próximo da máxima após range amplo")
    if not liquidity.get("passes_minimum", True):
        score -= 30
        reasons.append("liquidez abaixo do mínimo")
    return _clip(score), reasons


def score_asset(
    *,
    metrics: Mapping[str, Any],
    liquidity: Mapping[str, Any],
    trend: Mapping[str, Any] | None = None,
    weights: Mapping[str, float] | None = None,
) -> dict:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    score_momentum = _score_momentum(metrics)
    score_tendencia = _score_trend(trend)
    score_liquidez = _clip(to_float(liquidity.get("liquidity_score"), 0.0))
    score_volatilidade = _score_volatility(metrics)
    score_risco, risk_reasons = _score_risk(metrics, liquidity)

    weighted = (
        score_momentum * weights["momentum"]
        + score_tendencia * weights["tendencia"]
        + score_liquidez * weights["liquidez"]
        + score_volatilidade * weights["volatilidade"]
        + score_risco * weights["risco"]
    )

    return {
        "score_momentum": score_momentum,
        "score_tendencia": score_tendencia,
        "score_liquidez": score_liquidez,
        "score_volatilidade": score_volatilidade,
        "score_risco": score_risco,
        "score_final": _clip(weighted),
        "risk_reasons": risk_reasons,
        "metrics": dict(metrics),
        "liquidity": dict(liquidity),
    }
