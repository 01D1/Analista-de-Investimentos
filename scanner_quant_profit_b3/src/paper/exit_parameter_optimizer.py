"""Otimizacao exploratoria de parametros de saida para paper trading."""
from __future__ import annotations

import itertools
import json

import pandas as pd

from src.paper.simulator import run_paper_simulation


DEFAULT_PARAM_GRID = {
    "stop_loss_pct": [0.03, 0.05],
    "take_profit_pct": [0.06, 0.10],
    "trailing_stop_pct": [None, 0.04],
    "daily_loss_limit_pct": [None, 0.02],
    "atr_stop_multiplier": [None],
    "max_positions": [5],
    "risk_pct": [0.005],
}


def _iter_grid(param_grid: dict | None):
    grid = param_grid or DEFAULT_PARAM_GRID
    keys = list(grid.keys())
    values = [grid[k] if isinstance(grid[k], (list, tuple, set)) else [grid[k]] for k in keys]
    for combo in itertools.product(*values):
        yield dict(zip(keys, combo))


def _score(summary: dict, objective: str, min_trades: int) -> tuple[float, str]:
    total_return = float(summary.get("total_return", 0) or 0)
    max_drawdown = abs(float(summary.get("max_drawdown", 0) or 0))
    sharpe = float(summary.get("sharpe", 0) or 0)
    profit_factor = float(summary.get("profit_factor", 0) or 0)
    trades = int(summary.get("trades_count", summary.get("turnover", 0)) or 0)
    turnover = float(summary.get("turnover", trades) or 0)
    hints = []
    if trades < min_trades:
        hints.append("LOW_SAMPLE")
    if max_drawdown > 0.20:
        hints.append("HIGH_DRAWDOWN")
    if turnover > max(trades * 2, 250):
        hints.append("HIGH_TURNOVER")
    base = {
        "total_return": total_return,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "return_drawdown": total_return - max_drawdown,
    }.get(objective, total_return)
    penalty = 0.0
    if trades < min_trades:
        penalty += 1.0
    penalty += max_drawdown * 0.5
    if turnover > 250:
        penalty += 0.2
    return round(float(base - penalty), 6), ",".join(hints) if hints else "NORMAL"


def grid_search_exit_parameters(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    param_grid: dict | None = None,
    objective: str = "total_return",
    min_trades: int = 20,
    capital: float = 100_000,
    cost_bps: float = 10,
    slippage_bps: float = 5,
) -> pd.DataFrame:
    if prices_df is None or prices_df.empty or signals_df is None or signals_df.empty:
        return pd.DataFrame(
            columns=[
                "params_json",
                "total_return",
                "max_drawdown",
                "sharpe",
                "sortino",
                "win_rate",
                "profit_factor",
                "trades_count",
                "turnover",
                "score_objective",
                "overfit_risk_hint",
                "metadata_json",
            ]
        )
    rows = []
    for params in _iter_grid(param_grid):
        result = run_paper_simulation(
            signals_df,
            prices_df,
            risk_df=risk_df,
            capital=capital,
            max_positions=int(params.get("max_positions", 5) or 5),
            risk_pct=float(params.get("risk_pct", 0.005) or 0.005),
            cost_bps=cost_bps,
            slippage_bps=slippage_bps,
            stop_loss_pct=params.get("stop_loss_pct"),
            take_profit_pct=params.get("take_profit_pct"),
            trailing_stop_pct=params.get("trailing_stop_pct"),
            atr_stop_multiplier=params.get("atr_stop_multiplier"),
            daily_loss_limit_pct=params.get("daily_loss_limit_pct"),
            enable_rebalancing=False,
        )
        summary = result["performance_summary"]
        score, hint = _score(summary, objective, min_trades)
        rows.append(
            {
                "params_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
                "total_return": float(summary.get("total_return", 0) or 0),
                "max_drawdown": float(summary.get("max_drawdown", 0) or 0),
                "sharpe": float(summary.get("sharpe", 0) or 0),
                "sortino": float(summary.get("sortino", 0) or 0),
                "win_rate": float(summary.get("win_rate", 0) or 0),
                "profit_factor": float(summary.get("profit_factor", 0) or 0),
                "trades_count": int(summary.get("trades_count", summary.get("turnover", 0)) or 0),
                "turnover": float(summary.get("turnover", 0) or 0),
                "score_objective": score,
                "overfit_risk_hint": hint,
                "metadata_json": json.dumps({"objective": objective, "min_trades": min_trades}, ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def rank_exit_parameter_results(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame() if results_df is None else results_df.copy()
    df = results_df.copy()
    df["positive_return"] = pd.to_numeric(df["total_return"], errors="coerce").fillna(0) > 0
    df["controlled_drawdown"] = pd.to_numeric(df["max_drawdown"], errors="coerce").fillna(0).abs() <= 0.20
    df["enough_trades"] = pd.to_numeric(df["trades_count"], errors="coerce").fillna(0) >= 20
    df["pf_ok"] = pd.to_numeric(df["profit_factor"], errors="coerce").fillna(0) >= 1
    df["turnover_ok"] = pd.to_numeric(df["turnover"], errors="coerce").fillna(0) <= 250
    return df.sort_values(
        ["positive_return", "controlled_drawdown", "enough_trades", "pf_ok", "turnover_ok", "score_objective"],
        ascending=[False, False, False, False, False, False],
    ).reset_index(drop=True)


def generate_exit_parameter_report(results_df: pd.DataFrame) -> str:
    if results_df is None or results_df.empty:
        return "Otimizacao indisponivel: dados insuficientes para avaliar parametros simulados."
    ranked = rank_exit_parameter_results(results_df)
    best = ranked.iloc[0]
    return (
        "Melhor parametro em estudo: "
        f"{best.get('params_json')} com retorno simulado {float(best.get('total_return', 0)):.4f}, "
        f"drawdown {float(best.get('max_drawdown', 0)):.4f}, profit factor {float(best.get('profit_factor', 0)):.2f}. "
        f"Risco de ajuste: {best.get('overfit_risk_hint', 'NORMAL')}. "
        "A leitura e exploratoria e nao aplica parametros automaticamente."
    )
