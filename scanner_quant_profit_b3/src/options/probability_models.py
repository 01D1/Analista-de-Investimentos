"""
Probability Models — Probabilidade de Lucro por Estrutura

Usa distribuição lognormal (Black-Scholes) para estimar a probabilidade
de o ativo encerrar no range de lucro de cada estratégia no vencimento.

P(S_T > K) = N(d2)  onde d2 = [ln(S/K) + (r - 0.5σ²)T] / (σ√T)
"""
from __future__ import annotations

import math
from typing import List

from src.options.payoff_models import StrategyPayoff


# ---------------------------------------------------------------------------
# Distribuição normal padrão
# ---------------------------------------------------------------------------

def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _d2(S: float, K: float, T: float, sigma: float, r: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    return (math.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


# ---------------------------------------------------------------------------
# Primitivas de probabilidade
# ---------------------------------------------------------------------------

def prob_above(S: float, K: float, T: float, sigma: float, r: float) -> float:
    """P(S_T > K) — probabilidade do ativo superar K no vencimento."""
    return round(_norm_cdf(_d2(S, K, T, sigma, r)), 4)


def prob_below(S: float, K: float, T: float, sigma: float, r: float) -> float:
    """P(S_T < K)"""
    return round(1.0 - prob_above(S, K, T, sigma, r), 4)


def prob_between(S: float, K1: float, K2: float,
                 T: float, sigma: float, r: float) -> float:
    """P(K1 < S_T < K2) — probabilidade do ativo ficar entre dois níveis."""
    if K1 >= K2:
        K1, K2 = K2, K1
    return round(prob_above(S, K1, T, sigma, r) - prob_above(S, K2, T, sigma, r), 4)


# ---------------------------------------------------------------------------
# Probabilidade de lucro por estrutura
# ---------------------------------------------------------------------------

def prob_profit(payoff: StrategyPayoff, S: float, T: float,
                sigma: float, r: float) -> float:
    """
    Estima a probabilidade de lucro de uma estrutura no vencimento.

    Usa os breakevens analíticos da estrutura para calcular P(lucro > 0).
    """
    if T <= 0 or sigma <= 0:
        return 0.0

    bes = payoff.breakevens
    stype = payoff.strategy_type

    if not bes:
        return 0.0

    # Estratégias com 1 breakeven
    if stype in ("DIRECIONAL",):
        if "Long Call" in payoff.name or "Spread_Alta" in payoff.strategy_type:
            return prob_above(S, bes[0], T, sigma, r)
        if "Long Put" in payoff.name:
            return prob_below(S, bes[0], T, sigma, r)

    if stype == "SPREAD_ALTA":
        return prob_above(S, bes[0], T, sigma, r)

    if stype == "SPREAD_BAIXA":
        return prob_below(S, bes[0], T, sigma, r)

    # Iron Condor / Butterfly: lucro entre dois breakevens
    if stype in ("CONDOR", "BUTTERFLY") and len(bes) >= 2:
        return prob_between(S, bes[0], bes[1], T, sigma, r)

    # Straddle / Strangle: lucro fora dos dois breakevens
    if stype == "VOLATILIDADE" and len(bes) >= 2:
        return round(
            1.0 - prob_between(S, bes[0], bes[1], T, sigma, r), 4
        )

    # Renda (covered call, short options): 1 breakeven
    if stype == "RENDA" and bes:
        if "Covered" in payoff.name:
            return prob_above(S, bes[0], T, sigma, r)
        # short call spread (bear call): abaixo do breakeven
        if "Bear Call" in payoff.name:
            return prob_below(S, bes[0], T, sigma, r)
        # bull put spread (acima do breakeven)
        return prob_above(S, bes[0], T, sigma, r)

    # Proteção: sem sentido calcular probabilidade de lucro isolado
    if stype == "PROTECAO":
        return prob_above(S, bes[0], T, sigma, r)

    # Fallback genérico
    if len(bes) == 1:
        if payoff.net_cost > 0:  # débito → precisa subir
            return prob_above(S, bes[0], T, sigma, r)
        return prob_below(S, bes[0], T, sigma, r)

    return prob_between(S, bes[0], bes[1], T, sigma, r)


# ---------------------------------------------------------------------------
# Expected value aproximado
# ---------------------------------------------------------------------------

def expected_value(payoff: StrategyPayoff, S: float, T: float,
                   sigma: float, r: float) -> float:
    """
    EV aproximado = P(lucro) * max_profit - P(perda) * max_loss.
    Retorna inf se max_profit é ilimitado.
    """
    import math as _math
    p = prob_profit(payoff, S, T, sigma, r)
    mp = payoff.max_profit
    ml = payoff.max_loss
    if _math.isinf(mp) or _math.isinf(ml):
        return float("nan")
    ev = p * mp - (1 - p) * ml
    return round(ev, 2)
