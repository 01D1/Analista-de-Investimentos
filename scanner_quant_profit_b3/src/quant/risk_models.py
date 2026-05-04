"""
Modelos de risco: VaR, Kelly, position sizing, stop e alvos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Value at Risk
# ---------------------------------------------------------------------------

def value_at_risk(
    returns: pd.Series,
    confidence: float = 0.95,
    method: str = "historical",
) -> float:
    """
    VaR simplificado.

    method: "historical"  -> percentil empírico
            "parametric"  -> gaussiano
    Retorna a perda máxima esperada com a confiança dada (valor positivo).
    """
    clean = returns.dropna()
    if len(clean) == 0:
        return 0.0

    if method == "historical":
        return float(-np.percentile(clean, (1.0 - confidence) * 100.0))

    # Paramétrico
    mu = float(clean.mean())
    sigma = float(clean.std())
    from scipy.stats import norm
    z = norm.ppf(1.0 - confidence)
    return float(-(mu + z * sigma))


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """CVaR (Expected Shortfall) histórico — média das piores perdas além do VaR."""
    clean = returns.dropna()
    threshold = np.percentile(clean, (1.0 - confidence) * 100.0)
    tail = clean[clean <= threshold]
    return float(-tail.mean()) if len(tail) > 0 else 0.0


# ---------------------------------------------------------------------------
# Kelly
# ---------------------------------------------------------------------------

def kelly_fraction(
    win_rate: float,
    payoff_ratio: float,
    fraction: float = 0.25,
) -> float:
    """
    Fração de Kelly conservadora.

    f = (win_rate * payoff - (1 - win_rate)) / payoff * fraction
    fraction=0.25 = "quarter-Kelly" — padrão seguro para opções.
    """
    if payoff_ratio <= 0 or win_rate <= 0:
        return 0.0
    k = (win_rate * payoff_ratio - (1.0 - win_rate)) / payoff_ratio
    return round(max(k * fraction, 0.0), 4)


# ---------------------------------------------------------------------------
# Position sizing
# ---------------------------------------------------------------------------

def risk_amount(capital: float, risk_pct: float) -> float:
    """Capital arriscado por operação."""
    return capital * risk_pct


def position_size(
    capital: float,
    risk_pct: float,
    entry: float,
    stop: float,
    contract_size: int = 100,
) -> int:
    """
    Número de contratos de opção para não exceder o risco máximo.
    Assume que a perda máxima por contrato = (entry - stop) * contract_size.
    """
    if entry <= 0 or stop >= entry:
        return 0
    r = risk_amount(capital, risk_pct)
    risk_per_contract = (entry - stop) * contract_size
    if risk_per_contract <= 0:
        return 0
    return max(int(r / risk_per_contract), 0)


def financial_risk(
    contracts: int,
    entry: float,
    stop: float,
    contract_size: int = 100,
) -> float:
    """Risco financeiro real (R$) de uma posição."""
    return round(contracts * (entry - stop) * contract_size, 2)


# ---------------------------------------------------------------------------
# Stop & targets
# ---------------------------------------------------------------------------

def stop_price(entry: float, stop_pct: float) -> float:
    """Stop de perda: entry * (1 - stop_pct)."""
    return round(entry * (1.0 - stop_pct), 4)


def target_price(entry: float, target_pct: float) -> float:
    """Alvo: entry * (1 + target_pct)."""
    return round(entry * (1.0 + target_pct), 4)


def technical_stop(entry: float, atr_value: float, multiplier: float = 1.5) -> float:
    """Stop técnico baseado em ATR do ativo objeto."""
    return round(entry - atr_value * multiplier, 4)
