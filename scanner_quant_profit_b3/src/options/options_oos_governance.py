"""Governança fora da amostra para walk-forward de estruturas de opções."""
from __future__ import annotations

from typing import Any


def evaluate_options_walk_forward_governance(summary: dict[str, Any], limits: dict | None = None) -> dict[str, Any]:
    limits = {
        "min_windows": 3,
        "min_positive_windows_pct": 60,
        "min_mean_test_net_return": 0,
        "min_mean_test_win_rate": 52,
        "min_avg_test_trades": 5,
        "max_overfitting_windows_pct": 30,
        "max_cost_drag": 5,
        **(limits or {}),
    }
    windows = int(summary.get("windows_count") or 0)
    positive = float(summary.get("positive_windows_pct") or 0)
    mean_ret = float(summary.get("mean_test_net_return") or 0)
    win = float(summary.get("mean_test_win_rate") or 0)
    trades = float(summary.get("avg_test_trades") or 0)
    overfit = float(summary.get("overfitting_windows_count") or 0) / windows * 100 if windows else 100
    cost = float(summary.get("avg_cost_drag") or 0)
    robustness = str(summary.get("robustness_class") or "")
    reasons = []
    if windows < limits["min_windows"] or trades < limits["min_avg_test_trades"] or robustness == "OPTIONS_WF_DADOS_INSUFICIENTES":
        status = "OPTIONS_OOS_BLOCKED_INSUFFICIENT_DATA"
        reasons.append("dados ou janelas insuficientes")
    elif overfit > limits["max_overfitting_windows_pct"] or robustness == "OPTIONS_WF_OVERFIT_PROVAVEL":
        status = "OPTIONS_OOS_BLOCKED_OVERFITTING"
        reasons.append("degradação fora da amostra sugere overfitting")
    elif cost > limits["max_cost_drag"]:
        status = "OPTIONS_OOS_BLOCKED_COST_DRAG"
        reasons.append("custo médio elevado")
    elif positive >= limits["min_positive_windows_pct"] and mean_ret > limits["min_mean_test_net_return"] and win >= limits["min_mean_test_win_rate"]:
        status = "OPTIONS_OOS_APPROVED_FOR_STUDY"
        reasons.append("evidência OOS promissora apenas para estudo")
    elif mean_ret <= 0:
        status = "OPTIONS_OOS_BLOCKED_EXECUTION"
        reasons.append("retorno líquido de teste insuficiente")
    else:
        status = "OPTIONS_OOS_OBSERVATION_ONLY"
        reasons.append("resultado fora da amostra em observação")
    return {"governance_status": status, "approved": False, "reasons": reasons, "summary_text": generate_options_oos_governance_report({"governance_status": status, "reasons": reasons})}


def generate_options_oos_governance_report(review: dict[str, Any]) -> str:
    status = review.get("governance_status", "OPTIONS_OOS_OBSERVATION_ONLY")
    reasons = "; ".join(review.get("reasons", []))
    return f"Governança OOS de opções: {status}. {reasons}. Estrutura permanece apenas para estudo; não constitui recomendação."

