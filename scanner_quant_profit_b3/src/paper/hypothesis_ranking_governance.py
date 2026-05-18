"""Governança do ranking multi-fonte de hipóteses."""
from __future__ import annotations

import pandas as pd


def _num(row, col: str, default: float = 0.0) -> float:
    value = pd.to_numeric(pd.Series([row.get(col, default)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else default


def evaluate_ranked_hypothesis(row) -> dict:
    score = _num(row, "hypothesis_robustness_score")
    useful_sources = int(_num(row, "useful_sources_count"))
    positive = _num(row, "positive_improvement_pct")
    ret = _num(row, "mean_return_delta")
    drawdown = _num(row, "mean_drawdown_delta")
    frag = _num(row, "mean_fragility_delta")
    overfit = bool(row.get("overfitting_flag"))
    cost = bool(row.get("cost_sensitivity_flag"))
    low_coverage = bool(row.get("data_coverage_penalty", 0) >= 20) or useful_sources < 1

    if low_coverage:
        status = "HYPOTHESIS_RANK_BLOCKED_LOW_COVERAGE"
    elif overfit and score < 70:
        status = "HYPOTHESIS_RANK_BLOCKED_OVERFITTING"
    elif cost and score < 70:
        status = "HYPOTHESIS_RANK_BLOCKED_COST_SENSITIVE"
    elif score >= 70 and useful_sources >= 2 and positive >= 0.55 and ret >= 0 and drawdown >= 0 and frag < 0 and not overfit and not cost:
        status = "HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION"
    elif score >= 50 and frag < 0 and positive >= 0.40:
        status = "HYPOTHESIS_RANK_MORE_TESTING_REQUIRED"
    else:
        status = "HYPOTHESIS_RANK_REJECTED"

    return {
        "governance_status": status,
        "approved_for_observation": status == "HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION",
        "summary": "Hipótese robusta para observação." if status == "HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION" else "Hipótese bloqueada ou exige mais testes; não recomendação.",
    }

