"""Comparacao antes/depois de hipoteses de investigacao no paper trading."""
from __future__ import annotations

import pandas as pd


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def _get(summary: dict | pd.Series, key: str, default=0.0):
    if isinstance(summary, pd.Series):
        return summary.get(key, default)
    return summary.get(key, default)


def compare_investigation_to_base(base_summary: dict | pd.Series, investigation_summary: dict | pd.Series) -> dict:
    """Compara um experimento simulado contra o paper run base."""
    base_return = _num(_get(base_summary, "total_return"))
    inv_return = _num(_get(investigation_summary, "total_return", _get(investigation_summary, "simulated_return")))
    base_dd = _num(_get(base_summary, "max_drawdown"))
    inv_dd = _num(_get(investigation_summary, "max_drawdown", _get(investigation_summary, "simulated_drawdown")))
    base_pf = _num(_get(base_summary, "profit_factor"))
    inv_pf = _num(_get(investigation_summary, "profit_factor", _get(investigation_summary, "simulated_profit_factor")))
    base_wr = _num(_get(base_summary, "win_rate"))
    inv_wr = _num(_get(investigation_summary, "win_rate", _get(investigation_summary, "simulated_win_rate")))
    base_trades = int(_num(_get(base_summary, "trades_count")))
    inv_trades = int(_num(_get(investigation_summary, "trades_count", _get(investigation_summary, "simulated_trades"))))
    base_turnover = _num(_get(base_summary, "turnover"))
    inv_turnover = _num(_get(investigation_summary, "turnover"))
    base_fragility = _num(_get(base_summary, "fragility_score"))
    inv_fragility = _num(_get(investigation_summary, "fragility_score_after", _get(investigation_summary, "fragility_score")))
    base_cost = _num(_get(base_summary, "cost_drag"))
    inv_cost = _num(_get(investigation_summary, "cost_drag"))

    improved_return = inv_return > base_return
    reduced_drawdown = inv_dd > base_dd
    reduced_fragility = inv_fragility < base_fragility if base_fragility else False
    reduced_cost_drag = inv_cost < base_cost if base_cost else False
    sample_ratio = inv_trades / base_trades if base_trades else 0.0
    tradeoff_warning = ""
    if sample_ratio < 0.5:
        tradeoff_warning = "A melhora pode refletir reducao excessiva da amostra simulada."
    elif inv_return > base_return and inv_dd <= base_dd:
        tradeoff_warning = "Retorno melhorou, mas drawdown nao reduziu."
    elif inv_return <= base_return and reduced_drawdown:
        tradeoff_warning = "Drawdown reduziu, mas retorno nao melhorou."

    overfitting_warning = ""
    if inv_trades < 20:
        overfitting_warning = "Amostra baixa; risco de overfitting do experimento."
    elif improved_return and sample_ratio < 0.7:
        overfitting_warning = "Melhora depende de excluir parte relevante dos trades simulados."

    score = 0.0
    score += min(max((inv_return - base_return) * 400, -25), 35)
    score += 20 if reduced_drawdown else -10
    score += 20 if reduced_fragility else 0
    score += 10 if reduced_cost_drag else 0
    score += min(max((inv_pf - base_pf) * 10, -10), 15)
    score += min(max((inv_wr - base_wr) * 25, -10), 10)
    if sample_ratio < 0.5:
        score -= 25
    if inv_trades < 10:
        score -= 20
    improvement_score = round(max(min(score, 100), -100), 4)

    if inv_trades < 5:
        conclusion = "INVESTIGATION_INSUFFICIENT_DATA"
    elif improvement_score >= 35 and improved_return and (reduced_drawdown or reduced_fragility):
        conclusion = "INVESTIGATION_IMPROVED"
    elif improvement_score >= 10:
        conclusion = "INVESTIGATION_MIXED"
    elif improvement_score <= -10:
        conclusion = "INVESTIGATION_WORSE"
    else:
        conclusion = "INVESTIGATION_NO_IMPROVEMENT"

    return {
        "base_return": base_return,
        "simulated_return": inv_return,
        "base_drawdown": base_dd,
        "simulated_drawdown": inv_dd,
        "base_profit_factor": base_pf,
        "simulated_profit_factor": inv_pf,
        "base_win_rate": base_wr,
        "simulated_win_rate": inv_wr,
        "base_trades": base_trades,
        "simulated_trades": inv_trades,
        "base_turnover": base_turnover,
        "simulated_turnover": inv_turnover,
        "fragility_score_before": base_fragility,
        "fragility_score_after": inv_fragility,
        "cost_drag_before": base_cost,
        "cost_drag_after": inv_cost,
        "improvement_score": improvement_score,
        "improved_return": bool(improved_return),
        "reduced_drawdown": bool(reduced_drawdown),
        "reduced_fragility": bool(reduced_fragility),
        "reduced_cost_drag": bool(reduced_cost_drag),
        "tradeoff_warning": tradeoff_warning,
        "overfitting_warning": overfitting_warning,
        "conclusion": conclusion,
    }
