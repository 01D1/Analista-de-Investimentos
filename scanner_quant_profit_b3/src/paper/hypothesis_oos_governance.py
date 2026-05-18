"""Governanca OOS para hipoteses de investigacao do paper trading."""
from __future__ import annotations

import pandas as pd


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def evaluate_hypothesis_oos_governance(summary: dict | pd.Series) -> dict:
    row = summary.to_dict() if isinstance(summary, pd.Series) else dict(summary or {})
    windows = int(_num(row.get("windows_count")))
    scenarios = int(_num(row.get("scenarios_count")))
    positive_pct = _num(row.get("positive_improvement_pct"))
    mean_return_delta = _num(row.get("mean_return_delta"))
    mean_drawdown_delta = _num(row.get("mean_drawdown_delta"))
    mean_fragility_delta = _num(row.get("mean_fragility_delta"))
    cost_pct = _num(row.get("cost_sensitive_pct"))
    regime_pct = _num(row.get("regime_instability_pct"))
    overfit_pct = _num(row.get("overfitting_pct"))
    robustness_class = str(row.get("robustness_class", ""))

    reasons_for: list[str] = []
    reasons_against: list[str] = []
    required_actions = ["Manter como hipótese em validação; não aplicar automaticamente em paper recorrente ou capital real."]

    if positive_pct >= 0.60:
        reasons_for.append("Melhora positiva em pelo menos 60% das combinações OOS/cenário.")
    if mean_return_delta > 0:
        reasons_for.append("Delta médio de retorno foi positivo.")
    if mean_drawdown_delta >= 0:
        reasons_for.append("Drawdown médio não piorou frente ao baseline.")
    if mean_fragility_delta < 0:
        reasons_for.append("Fragility score médio reduziu.")
    if windows < 2 or scenarios < 3:
        reasons_against.append("Amostra OOS/cenários insuficiente.")
    if overfit_pct >= 0.5:
        reasons_against.append("Frequência alta de flags de overfitting.")
    if cost_pct >= 0.35:
        reasons_against.append("Sensibilidade a custo/slippage elevada.")
    if regime_pct >= 0.35:
        reasons_against.append("Instabilidade por regime elevada.")
    if mean_return_delta <= 0:
        reasons_against.append("Delta médio de retorno não foi positivo.")
    if mean_fragility_delta >= 0:
        reasons_against.append("Fragilidade média não reduziu.")

    if windows < 1 or scenarios < 1:
        status = "HYPOTHESIS_BLOCKED_LOW_SAMPLE"
        risk_level = "HIGH"
    elif overfit_pct >= 0.5 or robustness_class == "HYPOTHESIS_OVERFIT_PROBABLE":
        status = "HYPOTHESIS_BLOCKED_OVERFITTING"
        risk_level = "HIGH"
    elif cost_pct >= 0.35:
        status = "HYPOTHESIS_BLOCKED_COST_SENSITIVE"
        risk_level = "HIGH"
    elif regime_pct >= 0.35:
        status = "HYPOTHESIS_BLOCKED_REGIME_INSTABILITY"
        risk_level = "HIGH"
    elif robustness_class == "HYPOTHESIS_FRAGILE":
        status = "HYPOTHESIS_BLOCKED_NOT_ROBUST"
        risk_level = "MEDIUM"
    elif positive_pct >= 0.60 and mean_return_delta > 0 and mean_drawdown_delta >= 0 and mean_fragility_delta < 0 and windows >= 2 and scenarios >= 3:
        status = "HYPOTHESIS_APPROVED_FOR_RECURRENT_OBSERVATION"
        risk_level = "MEDIUM"
        required_actions.append("Registrar observação recorrente em novos períodos antes de qualquer interpretação operacional.")
    elif positive_pct >= 0.45 and mean_return_delta > 0:
        status = "HYPOTHESIS_APPROVED_FOR_MORE_TESTING"
        risk_level = "MEDIUM"
    elif positive_pct > 0:
        status = "HYPOTHESIS_OBSERVATION_ONLY"
        risk_level = "MEDIUM"
    else:
        status = "HYPOTHESIS_REJECTED"
        risk_level = "LOW"

    return {
        "governance_status": status,
        "approved_for_recurrent_observation": status == "HYPOTHESIS_APPROVED_FOR_RECURRENT_OBSERVATION",
        "risk_level": risk_level,
        "confidence_level": "LOW" if windows < 2 or scenarios < 3 else "MEDIUM",
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": required_actions,
    }
