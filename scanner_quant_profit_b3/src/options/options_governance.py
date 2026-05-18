"""Governança analítica para opções e estruturas."""
from __future__ import annotations

import math
from typing import Any


DEFAULT_LIMITS = {
    "max_spread_pct": 15,
    "min_financial_volume": 50_000,
    "min_dte": 7,
    "min_liquidity_score": 35,
}


def evaluate_option_candidate(option_row: dict | Any, limits: dict | None = None) -> dict:
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    get = option_row.get if hasattr(option_row, "get") else lambda k, default=None: getattr(option_row, k, default)
    reasons = []
    status = "OPTION_APPROVED_FOR_STUDY"
    if get("option_type") not in {"CALL", "PUT"} or get("strike") is None:
        return {"governance_status": "OPTION_BLOCKED_DATA", "approved_for_study": False, "reasons": ["dados insuficientes"]}
    spread = float(get("spread_pct") or 0)
    fin = float(get("financial_volume") or 0)
    dte = int(get("days_to_maturity") or 0)
    liq = float(get("liquidity_score") or 0)
    risk = float(get("risk_score") or 0)
    if spread > limits["max_spread_pct"]:
        status = "OPTION_BLOCKED_SPREAD"
        reasons.append("spread acima do limite")
    elif fin < limits["min_financial_volume"] or liq < limits["min_liquidity_score"]:
        status = "OPTION_BLOCKED_LIQUIDITY"
        reasons.append("liquidez insuficiente")
    elif dte < limits["min_dte"]:
        status = "OPTION_BLOCKED_EXPIRY"
        reasons.append("vencimento muito curto")
    elif risk and risk < 20:
        status = "OPTION_BLOCKED_RISK"
        reasons.append("risco elevado")
    if status == "OPTION_APPROVED_FOR_STUDY" and (liq < 55 or spread > limits["max_spread_pct"] * 0.75):
        status = "OPTION_OBSERVATION_ONLY"
        reasons.append("parâmetros exigem observação")
    return {"governance_status": status, "approved_for_study": status == "OPTION_APPROVED_FOR_STUDY", "reasons": reasons or ["apta apenas para estudo analítico"]}


def evaluate_structure_candidate(structure_row: dict | Any, limits: dict | None = None) -> dict:
    limits = {**DEFAULT_LIMITS, **(limits or {})}
    get = structure_row.get if hasattr(structure_row, "get") else lambda k, default=None: getattr(structure_row, k, default)
    reasons = []
    status = "STRUCTURE_APPROVED_FOR_STUDY"
    max_loss = get("max_loss")
    if max_loss is None or (isinstance(max_loss, float) and math.isnan(max_loss)):
        return {"governance_status": "STRUCTURE_BLOCKED_DATA", "approved_for_study": False, "reasons": ["max_loss não calculável"]}
    if math.isinf(float(max_loss)):
        status = "STRUCTURE_BLOCKED_RISK"
        reasons.append("risco ilimitado")
    elif float(get("liquidity_score") or 0) < limits["min_liquidity_score"]:
        status = "STRUCTURE_BLOCKED_LIQUIDITY"
        reasons.append("liquidez insuficiente nas pernas")
    elif float(get("risk_score") or 0) < 25:
        status = "STRUCTURE_BLOCKED_RISK"
        reasons.append("risco elevado")
    if status == "STRUCTURE_APPROVED_FOR_STUDY" and float(get("structure_score") or 0) < 65:
        status = "STRUCTURE_OBSERVATION_ONLY"
        reasons.append("score insuficiente para estudo prioritário")
    return {"governance_status": status, "approved_for_study": status == "STRUCTURE_APPROVED_FOR_STUDY", "reasons": reasons or ["apta apenas para estudo analítico"]}
