"""Governanca OOS das regras simuladas de paper trading."""
from __future__ import annotations


def evaluate_paper_oos_governance(summary: dict) -> dict:
    windows = int(summary.get("windows_count", 0) or 0)
    positive = float(summary.get("positive_windows_pct", 0) or 0)
    mean_return = float(summary.get("mean_test_return", 0) or 0)
    drawdown = abs(float(summary.get("mean_test_drawdown", 0) or 0))
    avg_trades = float(summary.get("avg_test_trades", 0) or 0)
    overfit = float(summary.get("overfitting_windows_pct", 0) or 0)
    robustness = str(summary.get("robustness_class", "")).upper()
    reasons_for = []
    reasons_against = []
    status = "PAPER_OOS_OBSERVATION_ONLY"
    if windows < 2 or "DADOS_INSUFICIENTES" in robustness:
        status = "PAPER_OOS_BLOCKED_DATA"
        reasons_against.append("Historico OOS insuficiente para robustez das regras simuladas.")
    elif overfit >= 0.40 or "OVERFIT" in robustness:
        status = "PAPER_OOS_BLOCKED_OVERFITTING"
        reasons_against.append("Treino favoravel nao se sustentou no teste em parte relevante das janelas.")
    elif mean_return < 0:
        status = "PAPER_OOS_BLOCKED_NEGATIVE_RETURN"
        reasons_against.append("Retorno medio fora da amostra ficou negativo.")
    elif drawdown > 0.20:
        status = "PAPER_OOS_BLOCKED_DRAWDOWN"
        reasons_against.append("Drawdown medio fora da amostra acima do limite analitico.")
    elif avg_trades < 10:
        status = "PAPER_OOS_BLOCKED_LOW_SAMPLE"
        reasons_against.append("Amostra media de trades simulados por janela e baixa.")
    elif positive >= 0.60 and mean_return > 0 and overfit == 0:
        status = "PAPER_OOS_APPROVED_FOR_STUDY"
        reasons_for.append("Regras simuladas apresentaram retorno OOS positivo e estabilidade minima.")
    else:
        reasons_for.append("Ha sinais parciais de robustez, ainda em observacao tecnica.")
    return {
        "governance_status": status,
        "approved_for_study": status == "PAPER_OOS_APPROVED_FOR_STUDY",
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": ["Comparar em novos periodos e manter parametros como estudo, sem aplicacao automatica."],
    }
