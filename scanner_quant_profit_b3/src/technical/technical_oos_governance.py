"""Governança fora da amostra para setups técnicos."""
from __future__ import annotations


def evaluate_technical_oos_candidate(summary: dict) -> dict:
    windows = int(summary.get("windows_count") or 0)
    positive = float(summary.get("positive_windows_pct") or 0)
    mean_ret = float(summary.get("mean_test_return") or 0)
    hit = float(summary.get("mean_test_hit_rate") or 0)
    avg_signals = float(summary.get("avg_test_signals") or 0)
    overfit = float(summary.get("overfitting_windows_pct") or 0)
    insufficient = float(summary.get("insufficient_windows_pct") or 0)
    robustness = str(summary.get("robustness_class") or "")
    reasons_for: list[str] = []
    reasons_against: list[str] = []
    status = "TECH_OOS_OBSERVATION_ONLY"
    if windows < 2 or insufficient >= 50 or robustness == "TECH_WF_DADOS_INSUFICIENTES":
        status = "TECH_OOS_BLOCKED_INSUFFICIENT_DATA"
        reasons_against.append("Poucas janelas ou poucos sinais fora da amostra.")
    elif overfit >= 40 or robustness == "TECH_WF_OVERFIT_PROVAVEL":
        status = "TECH_OOS_BLOCKED_OVERFITTING"
        reasons_against.append("Há degradação relevante entre treino e teste.")
    elif mean_ret <= 0:
        status = "TECH_OOS_BLOCKED_NEGATIVE_RETURN"
        reasons_against.append("Retorno médio fora da amostra não foi positivo.")
    elif positive >= 60 and hit >= 52 and avg_signals >= 30:
        status = "TECH_OOS_APPROVED_FOR_STUDY"
        reasons_for.append("Janelas positivas, retorno e hit rate superaram os limiares de estudo.")
    else:
        reasons_against.append("Resultado fora da amostra ainda é frágil para estudo mais forte.")
    if mean_ret > 0:
        reasons_for.append("Retorno médio OOS positivo.")
    return {
        "governance_status": status,
        "approved": False,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": ["Ampliar janela histórica", "Testar por regime/evento", "Reduzir redundância de setups"],
        "summary_text": f"Governança técnica OOS classificada como {status}. Não é recomendação operacional.",
    }


def generate_technical_oos_governance_report(review: dict) -> str:
    return review.get("summary_text", "Governança técnica OOS indisponível.")

