"""Explicações textuais auditáveis para sinais quantitativos."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def explain_signal(
    *,
    ticker: str,
    signal_type: str,
    metrics: Mapping[str, Any],
    liquidity: Mapping[str, Any],
    risks: Sequence[str] | None = None,
) -> str:
    reasons = []
    if metrics.get("position_range_pct") is not None:
        reasons.append(f"posição no range de {metrics['position_range_pct']}%")
    if metrics.get("variation_pct") is not None:
        reasons.append(f"variação de {metrics['variation_pct']}%")
    if liquidity.get("volume_ratio") is not None:
        reasons.append(f"volume relativo de {liquidity['volume_ratio']}x")

    text = f"{ticker} aparece no radar como {signal_type}"
    if reasons:
        text += " porque apresenta " + ", ".join(reasons)
    if risks:
        text += ". Pontos de atenção: " + "; ".join(risks)
    return text + "."
