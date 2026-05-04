"""
Dimensionamento de posição para a estratégia de opções.
Combina risk_models em uma interface de alto nível.
"""
from __future__ import annotations

from .risk_models import (
    risk_amount,
    position_size,
    financial_risk,
    stop_price,
    target_price,
    kelly_fraction,
)


def compute_sizing(
    capital: float,
    risk_pct: float,
    entry: float,
    stop_pct: float,
    target1_pct: float,
    target2_pct: float,
    win_rate_est: float = 0.45,
    contract_size: int = 100,
) -> dict:
    """
    Calcula o dimensionamento completo de uma operação de opção.

    Args:
        capital:      capital total disponível
        risk_pct:     % do capital arriscado por trade (ex: 0.005 = 0.5%)
        entry:        preço de entrada na opção (prêmio)
        stop_pct:     % de perda no prêmio que aciona o stop (ex: 0.30 = 30%)
        target1_pct:  % de ganho no prêmio para alvo 1 (ex: 0.50 = 50%)
        target2_pct:  % de ganho no prêmio para alvo 2 (ex: 1.00 = 100%)
        win_rate_est: estimativa de taxa de acerto para Kelly
        contract_size: lote padrão (100 ações por contrato na B3)

    Returns:
        Dicionário com contracts, entry, stop, alvo_1, alvo_2,
        risco_financeiro, payoff_ratio, kelly_fraction.
    """
    stop = stop_price(entry, stop_pct)
    alvo1 = target_price(entry, target1_pct)
    alvo2 = target_price(entry, target2_pct)

    contracts = position_size(capital, risk_pct, entry, stop, contract_size)
    fin_risk = financial_risk(contracts, entry, stop, contract_size)

    payoff = target1_pct / stop_pct if stop_pct > 0 else 0.0
    kelly = kelly_fraction(win_rate_est, payoff)

    return {
        "contracts": contracts,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "alvo_1": round(alvo1, 4),
        "alvo_2": round(alvo2, 4),
        "risco_financeiro": round(fin_risk, 2),
        "risco_pct_capital": round(fin_risk / capital * 100, 3) if capital > 0 else 0.0,
        "payoff_ratio": round(payoff, 2),
        "kelly_fraction": round(kelly, 4),
    }
