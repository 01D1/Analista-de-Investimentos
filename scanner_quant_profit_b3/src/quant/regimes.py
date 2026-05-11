"""Classificação simples de regimes de mercado."""
from __future__ import annotations

import pandas as pd

from .indicators import sma
from .volatility import historical_volatility


def classify_market_regime(close: pd.Series, short_window: int = 9, long_window: int = 21) -> dict:
    clean = pd.to_numeric(close, errors="coerce").dropna()
    if len(clean) < max(short_window, long_window):
        return {"trend_regime": "INDEFINIDO", "volatility_regime": "INDEFINIDO", "risk_regime": "INDEFINIDO"}

    short_ma = sma(clean, short_window).iloc[-1]
    long_ma = sma(clean, long_window).iloc[-1]
    last = clean.iloc[-1]

    if last > short_ma > long_ma:
        trend = "TENDENCIA_DE_ALTA"
    elif last < short_ma < long_ma:
        trend = "TENDENCIA_DE_BAIXA"
    else:
        trend = "LATERAL"

    hv = historical_volatility(clean, window=min(21, len(clean) - 1)).dropna()
    current_hv = float(hv.iloc[-1]) if not hv.empty else 0.0
    vol_regime = "ALTA_VOLATILIDADE" if current_hv >= 0.35 else ("BAIXA_VOLATILIDADE" if current_hv <= 0.15 else "VOLATILIDADE_MEDIA")
    risk_regime = "APETITE_A_RISCO" if trend == "TENDENCIA_DE_ALTA" and vol_regime != "ALTA_VOLATILIDADE" else "NEUTRO"

    return {
        "trend_regime": trend,
        "volatility_regime": vol_regime,
        "risk_regime": risk_regime,
        "historical_volatility": round(current_hv, 4),
    }
