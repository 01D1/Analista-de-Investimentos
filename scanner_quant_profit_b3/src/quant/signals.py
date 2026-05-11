"""Classificação textual de sinais quantitativos."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .metrics import to_float


def classify_asset_signal(score_result: Mapping[str, Any]) -> dict:
    metrics = score_result.get("metrics", {}) or {}
    liquidity = score_result.get("liquidity", {}) or {}
    score_final = to_float(score_result.get("score_final"), 0.0)
    score_liquidez = to_float(score_result.get("score_liquidez"), 0.0)
    score_momentum = to_float(score_result.get("score_momentum"), 0.0)
    score_risco = to_float(score_result.get("score_risco"), 0.0)
    position = to_float(metrics.get("position_range_pct"), 0.0)
    range_pct = to_float(metrics.get("range_pct"), 0.0)
    volume_ratio = to_float(liquidity.get("volume_ratio"), 1.0)

    if score_risco < 45 and position >= 90:
        signal_type = "ESTICADO / RISCO DE PULLBACK"
    elif score_final >= 80 and score_liquidez >= 70 and position >= 85 and volume_ratio >= 1.5:
        signal_type = "ROMPIMENTO COM VOLUME"
    elif score_final >= 75 and score_liquidez >= 70:
        signal_type = "FORÇA COM LIQUIDEZ"
    elif score_momentum <= 30 and volume_ratio >= 1.5:
        signal_type = "FRAQUEZA COM VOLUME"
    elif position <= 25 and range_pct >= 4:
        signal_type = "REVERSÃO POSSÍVEL"
    elif score_final < 45:
        signal_type = "SEM ASSIMETRIA"
    elif score_final >= 60:
        signal_type = "OBSERVAR"
    else:
        signal_type = "NEUTRO"

    return {
        "signal_type": signal_type,
        "confidence": "ALTA" if score_final >= 80 and score_risco >= 60 else ("MEDIA" if score_final >= 60 else "BAIXA"),
    }
