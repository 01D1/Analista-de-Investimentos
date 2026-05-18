"""Governança de risco."""
from __future__ import annotations

import json
import pandas as pd


def _num(row, key, default=0.0):
    v = pd.to_numeric(pd.Series([row.get(key, default) if hasattr(row, "get") else default]), errors="coerce").iloc[0]
    return float(v) if pd.notna(v) else default


def evaluate_risk_snapshot(row) -> dict:
    reasons_for = []
    reasons_against = []
    actions = []
    status = "RISK_OK"
    risk_level = "BAIXO"
    confidence = "MEDIA"
    vol = _num(row, "ensemble_vol", float("nan"))
    var = _num(row, "parametric_var_95", 0)
    position = _num(row, "position_value", 0)
    size = _num(row, "recommended_size", 0)
    regime = str(row.get("volatility_regime", "")).upper()
    if pd.isna(vol) or position <= 0:
        status = "RISK_BLOCKED_DATA"
        risk_level = "ALTO"
        confidence = "BAIXA"
        reasons_against.append("Dados insuficientes para risco.")
        actions.append("Coletar histórico diário suficiente antes de avaliar risco.")
    elif regime == "VOL_EXTREMA" or vol >= 0.60:
        status = "RISK_BLOCKED_VOLATILITY"
        risk_level = "ALTO"
        reasons_against.append("Volatilidade estimada extrema.")
    elif position > 0 and var / position > 0.05:
        status = "RISK_BLOCKED_VAR"
        risk_level = "ALTO"
        reasons_against.append("VaR acima do limite analítico.")
    elif size <= 0:
        status = "RISK_BLOCKED_LIQUIDITY"
        risk_level = "ALTO"
        reasons_against.append("Sizing final nulo ou insuficiente.")
    elif regime in {"VOL_ALTA", "VOL_EXPANDINDO"}:
        status = "RISK_WARNING"
        risk_level = "MEDIO"
        reasons_against.append("Risco estimado elevado.")
    else:
        reasons_for.append("Risco estimado dentro dos limites analíticos.")
    return {"risk_status": status, "risk_level": risk_level, "confidence_level": confidence, "reasons_for_json": json.dumps(reasons_for, ensure_ascii=False), "reasons_against_json": json.dumps(reasons_against, ensure_ascii=False), "required_actions_json": json.dumps(actions, ensure_ascii=False)}


def generate_risk_governance_report(review: dict) -> str:
    return f"Status de risco: {review.get('risk_status')}. Nível: {review.get('risk_level')}. Confiança: {review.get('confidence_level')}."

