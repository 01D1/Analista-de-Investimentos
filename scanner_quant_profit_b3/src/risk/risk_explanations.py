"""Explicações textuais de risco."""
from __future__ import annotations


def explain_volatility(row) -> str:
    return f"Regime de volatilidade {row.get('volatility_regime', 'DADOS_INSUFICIENTES')}, com ensemble_vol {row.get('ensemble_vol', '-')}. "


def explain_var(row) -> str:
    return f"VaR 95% estimado em {row.get('parametric_var_95', '-')}, para valor de posição {row.get('position_value', '-')}. "


def explain_sizing(row) -> str:
    return f"Sizing sugerido para estudo limitado por {row.get('limiting_factor', 'DATA_INSUFFICIENT')}, com tamanho {row.get('recommended_size', '-')}. "


def explain_risk_governance(row) -> str:
    return f"Governança de risco: {row.get('risk_status', 'RISK_BLOCKED_DATA')}. "

