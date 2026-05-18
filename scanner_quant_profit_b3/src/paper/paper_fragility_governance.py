"""Governanca de fragilidade da carteira simulada."""
from __future__ import annotations


def evaluate_fragility_governance(fragility_summary: dict) -> dict:
    score = float(fragility_summary.get("fragility_score", 100) or 100)
    trades = int(fragility_summary.get("total_trades", 0) or 0)
    cost_drag = float(fragility_summary.get("cost_drag_pct", 0) or 0)
    max_dd = abs(float(fragility_summary.get("max_drawdown", 0) or 0))
    concentration = float(fragility_summary.get("top_asset_contribution_pct", 0) or 0)
    signal_fragile = bool(fragility_summary.get("signal_source_fragile", False))
    reasons_for = []
    reasons_against = []
    if trades < 5:
        status = "PAPER_FRAGILITY_BLOCKED_DATA"
        reasons_against.append("Amostra insuficiente para diagnostico de fragilidade.")
    elif cost_drag > 0.50:
        status = "PAPER_FRAGILITY_BLOCKED_COST"
        reasons_against.append("Custo/slippage domina parte relevante do P&L simulado.")
    elif max_dd > 0.20:
        status = "PAPER_FRAGILITY_BLOCKED_DRAWDOWN"
        reasons_against.append("Drawdown concentrado acima do limite analitico.")
    elif concentration > 0.60:
        status = "PAPER_FRAGILITY_BLOCKED_CONCENTRATION"
        reasons_against.append("Poucos ativos explicam parte excessiva do resultado.")
    elif signal_fragile:
        status = "PAPER_FRAGILITY_BLOCKED_SIGNAL_SOURCE"
        reasons_against.append("Fonte de sinal em observacao apresenta fragilidade.")
    elif score < 35:
        status = "PAPER_FRAGILITY_OK"
        reasons_for.append("Fragility score geral dentro de faixa observacional aceitavel.")
    else:
        status = "PAPER_FRAGILITY_OBSERVATION"
        reasons_against.append("Fragilidade detectada requer investigacao adicional.")
    return {"governance_status": status, "reasons_for": reasons_for, "reasons_against": reasons_against, "required_actions": ["Investigar contribuicoes negativas antes de qualquer uso operacional."]}
