"""Governança integrada entre técnico, quant, valuation, eventos, regimes e opções."""
from __future__ import annotations

import pandas as pd

from src.integration.integrated_explanations import generate_reasons_against, generate_reasons_for, generate_required_actions


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def evaluate_integrated_governance(row) -> dict:
    data_quality = _num(row.get("data_quality_score"))
    blocked_values = [str(row.get(c, "")).upper() for c in ["technical_oos_status", "quant_governance_status", "event_governance_status", "option_oos_governance_status", "risk_status"]]
    reasons_for = generate_reasons_for(row)
    reasons_against = generate_reasons_against(row)
    status = "INTEGRATED_OBSERVATION_ONLY"
    risk = "MEDIO"
    confidence = "MEDIA"
    risk_status = str(row.get("risk_status", "")).upper()
    if data_quality < 35:
        status = "INTEGRATED_BLOCKED_DATA"
        risk = "ALTO"
        confidence = "BAIXA"
    elif "RISK_BLOCKED" in risk_status:
        status = "INTEGRATED_BLOCKED_GOVERNANCE"
        risk = "ALTO"
        confidence = "BAIXA"
    elif risk_status == "RISK_WARNING":
        status = "INTEGRATED_REQUIRES_REVIEW"
        risk = "MEDIO_ALTO"
        confidence = "MEDIA"
    elif any("BLOCKED" in v or "BLOQUEADO" in v for v in blocked_values):
        status = "INTEGRATED_BLOCKED_GOVERNANCE"
        risk = "ALTO"
        confidence = "BAIXA"
    elif str(row.get("event_governance_status", "")).upper() == "EVENT_COVERAGE_WEAK":
        status = "INTEGRATED_REQUIRES_REVIEW"
        confidence = "BAIXA"
    elif str(row.get("option_oos_governance_status", "")).upper().endswith("LIQUIDITY"):
        status = "INTEGRATED_BLOCKED_LIQUIDITY"
        risk = "ALTO"
    elif len(reasons_for) >= 3:
        status = "INTEGRATED_APPROVED_FOR_STUDY"
        risk = "MEDIO"
        confidence = "MEDIA_ALTA"
    elif len(reasons_for) <= 1 and len(reasons_against) >= 2:
        status = "INTEGRATED_DIVERGENT_SIGNALS"
    return {
        "integrated_governance_status": status,
        "approved_for_study": False,
        "risk_level": risk,
        "confidence_level": confidence,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": generate_required_actions(row),
    }
