"""Explicacoes textuais para setups e score tecnico."""
from __future__ import annotations

import json

import pandas as pd


def _reasons(value) -> list[str]:
    if isinstance(value, list):
        return value
    if not value or pd.isna(value):
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        return [str(value)]


def explain_technical_setup(row) -> str:
    setup = row.get("setup_type", "setup técnico")
    ticker = row.get("ticker", "ativo")
    reasons = _reasons(row.get("reasons_for"))
    score = row.get("setup_score", row.get("technical_score_final", "-"))
    detail = "; ".join(reasons[:3]) if reasons else "critérios objetivos parametrizados foram atendidos"
    return (
        f"{ticker} apresentou {setup} porque {detail}. "
        f"O score técnico do padrão foi {score}. Trata-se de padrão a investigar, não recomendação operacional."
    )


def explain_technical_score(row) -> str:
    status = row.get("technical_status", "INDEFINIDO")
    score = row.get("technical_score_final", "-")
    trend = row.get("trend_short", "INDEFINIDO")
    momentum = row.get("momentum_state", "INDEFINIDO")
    vol = row.get("volatility_regime", "INDEFINIDO")
    return (
        f"Score técnico {score} classificado como {status}. "
        f"Tendência curta: {trend}; momentum: {momentum}; volatilidade: {vol}. "
        "A leitura é diagnóstica e não altera o ranking principal."
    )

