"""Governanca das hipoteses de investigacao do paper trading."""
from __future__ import annotations

import pandas as pd


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def evaluate_investigation_result(comparison_row: dict | pd.Series) -> dict:
    row = comparison_row if isinstance(comparison_row, dict) else comparison_row.to_dict()
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    required_actions: list[str] = ["Validar a hipotese em multi-cenario e fora da amostra antes de qualquer uso analitico recorrente."]

    improvement_score = _num(row.get("improvement_score"))
    simulated_trades = int(_num(row.get("simulated_trades")))
    improved_return = bool(row.get("improved_return"))
    reduced_drawdown = bool(row.get("reduced_drawdown"))
    reduced_fragility = bool(row.get("reduced_fragility"))
    overfitting_warning = str(row.get("overfitting_warning") or "")
    tradeoff_warning = str(row.get("tradeoff_warning") or "")

    if improved_return:
        reasons_for.append("Retorno simulado melhorou frente ao caso base.")
    if reduced_drawdown:
        reasons_for.append("Drawdown simulado reduziu frente ao caso base.")
    if reduced_fragility:
        reasons_for.append("Fragility score simulado reduziu.")
    if simulated_trades < 20:
        reasons_against.append("Amostra simulada baixa.")
    if overfitting_warning:
        reasons_against.append(overfitting_warning)
    if tradeoff_warning:
        reasons_against.append(tradeoff_warning)

    if simulated_trades < 5:
        status = "INVESTIGATION_BLOCKED_LOW_SAMPLE"
        risk_level = "HIGH"
    elif overfitting_warning and improvement_score > 0:
        status = "INVESTIGATION_BLOCKED_OVERFITTING"
        risk_level = "HIGH"
    elif tradeoff_warning and improvement_score < 35:
        status = "INVESTIGATION_BLOCKED_TRADEOFF"
        risk_level = "MEDIUM"
    elif improvement_score >= 35 and improved_return and (reduced_drawdown or reduced_fragility):
        status = "INVESTIGATION_APPROVED_FOR_FURTHER_TEST"
        risk_level = "MEDIUM"
    elif improvement_score >= 10:
        status = "INVESTIGATION_OBSERVATION_ONLY"
        risk_level = "MEDIUM"
    else:
        status = "INVESTIGATION_REJECTED"
        risk_level = "LOW"

    confidence_level = "LOW" if simulated_trades < 20 else "MEDIUM"
    if status == "INVESTIGATION_APPROVED_FOR_FURTHER_TEST" and simulated_trades >= 40:
        confidence_level = "MEDIUM"

    return {
        "governance_status": status,
        "approved_for_further_test": status == "INVESTIGATION_APPROVED_FOR_FURTHER_TEST",
        "risk_level": risk_level,
        "confidence_level": confidence_level,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": required_actions,
    }
