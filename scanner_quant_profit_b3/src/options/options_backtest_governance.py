"""Governança do backtest preliminar de estruturas de opções."""
from __future__ import annotations

from typing import Any


def evaluate_options_backtest_candidate(summary: dict[str, Any], limits: dict | None = None) -> dict[str, Any]:
    limits = {
        "min_trades": 30,
        "min_completed": 20,
        "min_win_rate": 52,
        "min_mean_net_return": 0,
        "min_profit_factor": 1.1,
        "max_avg_cost_drag": 5,
        "max_skipped_pct": 40,
        **(limits or {}),
    }
    total = int(summary.get("total_trades") or 0)
    completed = int(summary.get("completed_count") or 0)
    skipped = int(summary.get("skipped_count") or 0)
    skipped_pct = skipped / total * 100 if total else 100
    reasons = []
    status = "OPTIONS_BACKTEST_PROMISSOR"
    if total <= 0:
        status = "OPTIONS_BACKTEST_BLOQUEADO_DADOS"
        reasons.append("sem histórico de cadeia suficiente")
    elif total < limits["min_trades"] or completed < limits["min_completed"]:
        status = "OPTIONS_BACKTEST_BLOQUEADO_AMOSTRA"
        reasons.append("amostra insuficiente")
    elif skipped_pct > limits["max_skipped_pct"]:
        status = "OPTIONS_BACKTEST_BLOQUEADO_EXECUCAO"
        reasons.append("muitos trades pulados por execução/dados")
    elif float(summary.get("avg_cost_drag") or 0) > limits["max_avg_cost_drag"]:
        status = "OPTIONS_BACKTEST_BLOQUEADO_EXECUCAO"
        reasons.append("custo médio elevado")
    elif float(summary.get("mean_net_return") or 0) <= limits["min_mean_net_return"] or float(summary.get("profit_factor") or 0) < limits["min_profit_factor"]:
        status = "OPTIONS_BACKTEST_REJEITADO"
        reasons.append("retorno líquido ou profit factor insuficiente")
    elif float(summary.get("win_rate") or 0) < limits["min_win_rate"]:
        status = "OPTIONS_BACKTEST_EM_OBSERVACAO"
        reasons.append("win rate abaixo do mínimo")
    return {
        "governance_status": status,
        "approved": False,
        "reasons": reasons or ["resultado apenas promissor para estudo estatístico"],
        "summary_text": "Governança de opções não promove estruturas a uso operacional; apenas classifica evidência preliminar.",
    }

