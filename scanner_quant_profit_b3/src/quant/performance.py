"""
Performance Analytics — Quant Research Layer.

Métricas completas de performance para avaliação de estratégias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Métricas elementares
# ---------------------------------------------------------------------------

def drawdown(equity: pd.Series) -> tuple[pd.Series, float]:
    """Série de drawdown e máximo drawdown (negativo)."""
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    return dd, float(dd.min())


def sharpe_ratio(
    returns: pd.Series,
    risk_free_annual: float = 0.1475,
    periods_per_year: int = 252,
) -> float:
    clean = returns.dropna()
    if len(clean) < 2 or clean.std() == 0:
        return 0.0
    rf = risk_free_annual / periods_per_year
    excess = clean - rf
    return float((excess.mean() / clean.std()) * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: pd.Series,
    risk_free_annual: float = 0.1475,
    periods_per_year: int = 252,
) -> float:
    clean = returns.dropna()
    if len(clean) < 2:
        return 0.0
    rf = risk_free_annual / periods_per_year
    downside = clean[clean < 0]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    excess = clean.mean() - rf
    return float((excess / downside.std()) * np.sqrt(periods_per_year))


def calmar_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = returns.dropna()
    if len(clean) == 0:
        return 0.0
    equity = (1.0 + clean).cumprod()
    _, max_dd = drawdown(equity)
    if max_dd == 0:
        return 0.0
    annual_return = float(clean.mean()) * periods_per_year
    return float(annual_return / abs(max_dd))


def win_rate(pnl: pd.Series) -> float:
    clean = pnl.dropna()
    return float((clean > 0).sum() / len(clean)) if len(clean) > 0 else 0.0


def payoff_ratio(pnl: pd.Series) -> float:
    clean = pnl.dropna()
    winners = clean[clean > 0]
    losers = clean[clean < 0].abs()
    if len(losers) == 0 or losers.mean() == 0:
        return 0.0
    avg_win = winners.mean() if len(winners) > 0 else 0.0
    return float(avg_win / losers.mean())


def profit_factor(pnl: pd.Series) -> float:
    """Soma dos ganhos / soma das perdas absolutas. >1 = sistema lucrativo."""
    clean = pnl.dropna()
    total_wins = clean[clean > 0].sum()
    total_losses = clean[clean < 0].abs().sum()
    return round(float(total_wins / total_losses), 4) if total_losses > 0 else float("inf")


def expectancy(win_rate_val: float, avg_win: float, avg_loss: float) -> float:
    """E = WR × avgWin − (1−WR) × avgLoss. Positivo = sistema lucrativo."""
    return float(win_rate_val * avg_win - (1.0 - win_rate_val) * avg_loss)


# ---------------------------------------------------------------------------
# Sumário completo
# ---------------------------------------------------------------------------

def full_summary(pnl: pd.Series, capital: float = 10_000.0) -> dict:
    """
    Sumário completo de performance a partir de uma série de P&L por trade.
    Retorna todas as métricas usadas pela Quant Research Layer.
    """
    clean = pnl.dropna()
    if len(clean) == 0:
        return {}

    returns = clean / capital
    equity = (1.0 + returns).cumprod() * capital
    _, max_dd = drawdown(equity)

    wr = win_rate(clean)
    pr = payoff_ratio(clean)
    pf = profit_factor(clean)
    winners = clean[clean > 0]
    losers = clean[clean < 0].abs()
    avg_win = float(winners.mean()) if len(winners) > 0 else 0.0
    avg_loss = float(losers.mean()) if len(losers) > 0 else 0.0
    best = float(clean.max()) if len(clean) > 0 else 0.0
    worst = float(clean.min()) if len(clean) > 0 else 0.0
    avg_trade = float(clean.mean()) if len(clean) > 0 else 0.0
    total_return_pct = round((float(equity.iloc[-1]) / capital - 1.0) * 100.0, 2)

    return {
        "total_trades": len(clean),
        "win_rate": round(wr, 4),
        "payoff_ratio": round(pr, 4),
        "profit_factor": round(pf, 4) if pf != float("inf") else 999.0,
        "expectancy": round(expectancy(wr, avg_win, avg_loss), 2),
        "avg_trade": round(avg_trade, 2),
        "best_trade": round(best, 2),
        "worst_trade": round(worst, 2),
        "total_pnl": round(float(clean.sum()), 2),
        "total_return_pct": total_return_pct,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_dd, 4),
        "sharpe": round(sharpe_ratio(returns), 4),
        "sortino": round(sortino_ratio(returns), 4),
        "calmar": round(calmar_ratio(returns), 4),
        "final_capital": round(float(equity.iloc[-1]), 2),
    }


# Alias de compatibilidade com código legado
def summary_stats(pnl: pd.Series, capital: float = 10_000.0) -> dict:
    return full_summary(pnl, capital)
