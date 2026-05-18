"""Governanca tecnica: classifica setups sem promover operacao."""
from __future__ import annotations

import pandas as pd


DEFAULT_RULES = {
    "min_samples": 30,
    "min_mean_return_5d": 0.0,
    "min_hit_rate_5d": 52.0,
    "max_high_volatility_pct": 50.0,
}


def _as_dict(summary) -> dict:
    if isinstance(summary, pd.Series):
        return summary.to_dict()
    if isinstance(summary, pd.DataFrame):
        return summary.iloc[0].to_dict() if not summary.empty else {}
    return dict(summary or {})


def evaluate_technical_setup_candidate(summary, rules: dict | None = None) -> dict:
    rules = {**DEFAULT_RULES, **(rules or {})}
    metrics = _as_dict(summary)
    signals = int(metrics.get("signals") or metrics.get("signals_count") or 0)
    mean_ret = float(metrics.get("mean_net_return_5d", metrics.get("mean_return_5d", 0)) or 0)
    hit = float(metrics.get("hit_rate_5d", 0) or 0)
    status = "TECH_OBSERVATION_ONLY"
    reasons_for = []
    reasons_against = []
    if signals < rules["min_samples"]:
        status = "TECH_BLOCKED_INSUFFICIENT_DATA"
        reasons_against.append("Amostra abaixo do mínimo configurado.")
    elif mean_ret <= rules["min_mean_return_5d"]:
        status = "TECH_BLOCKED_NEGATIVE_NET_RETURN"
        reasons_against.append("Retorno médio líquido/bruto de 5 dias não é positivo.")
    elif str(metrics.get("volatility_regime", "")).upper() == "ALTA_VOLATILIDADE":
        status = "TECH_BLOCKED_HIGH_VOLATILITY"
        reasons_against.append("Setup concentrado em alta volatilidade.")
    elif hit >= rules["min_hit_rate_5d"]:
        status = "TECH_APPROVED_FOR_STUDY"
        reasons_for.append("Amostra mínima, retorno positivo e hit rate acima do limiar para estudo.")
    else:
        reasons_against.append("Métricas positivas, mas ainda sem robustez suficiente.")
    if mean_ret > 0:
        reasons_for.append("Retorno médio de 5 dias positivo na amostra analisada.")
    return {
        "governance_status": status,
        "approved": False,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
        "required_actions": ["Validar fora da amostra", "Aplicar custos/slippage quando disponíveis", "Verificar estabilidade por regime"],
        "summary_text": f"Setup técnico classificado como {status}. A classificação é analítica e não constitui recomendação.",
    }

