"""Ajuste de exposição simulada por regime."""
from __future__ import annotations


def adjust_exposure_by_regime(base_exposure, regime_row) -> dict:
    text = " ".join(str(regime_row.get(c, "")) for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"]) if regime_row is not None else ""
    upper = text.upper()
    factor = 1.0
    reason = "Regime sem ajuste de exposição simulada."
    if "RISCO_ELEVADO" in upper:
        factor = 0.0
        reason = "Regime de risco elevado bloqueia novas entradas simuladas."
    elif "BAIXA_TENDENCIAL" in upper:
        factor = 0.35
        reason = "Baixa tendencial reduz fortemente a exposição simulada."
    elif "ALTA_VOLATILIDADE" in upper or "VOL_ALTA" in upper:
        factor = 0.50
        reason = "Alta volatilidade reduz exposição simulada."
    elif "LIQUIDEZ_FRACA" in upper:
        factor = 0.50
        reason = "Liquidez fraca reduz exposição simulada."
    elif "LATERAL" in upper:
        factor = 0.70
        reason = "Regime lateral reduz exposição simulada."
    elif "ALTA_TENDENCIAL" in upper:
        factor = 1.0
        reason = "Alta tendencial mantém exposição simulada normal."
    return {"adjusted_exposure": float(base_exposure) * factor, "regime_adjustment_factor": factor, "reason": reason}

