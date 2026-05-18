"""Walk-forward das regras simuladas de saida do paper trading."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.exit_parameter_optimizer import grid_search_exit_parameters, rank_exit_parameter_results
from src.paper.simulator import run_paper_simulation


RESULT_COLUMNS = [
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_params_json",
    "train_return",
    "test_return",
    "train_drawdown",
    "test_drawdown",
    "train_profit_factor",
    "test_profit_factor",
    "train_trades",
    "test_trades",
    "test_positive",
    "overfitting_flag",
    "turnover_warning",
    "drawdown_warning",
    "metadata_json",
]


def create_paper_walk_forward_windows(start_date, end_date, train_months: int = 2, test_months: int = 1) -> pd.DataFrame:
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    rows = []
    idx = 1
    cursor = start
    while cursor < end:
        train_start = cursor
        train_end = train_start + pd.DateOffset(months=train_months) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = test_start + pd.DateOffset(months=test_months) - pd.Timedelta(days=1)
        if test_start > end:
            break
        rows.append(
            {
                "window_id": idx,
                "train_start": train_start.date().isoformat(),
                "train_end": min(train_end, end).date().isoformat(),
                "test_start": test_start.date().isoformat(),
                "test_end": min(test_end, end).date().isoformat(),
            }
        )
        idx += 1
        cursor = test_start
    return pd.DataFrame(rows, columns=["window_id", "train_start", "train_end", "test_start", "test_end"])


def _slice(df: pd.DataFrame | None, start: str, end: str) -> pd.DataFrame:
    if df is None or df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["trade_date"] = work["trade_date"].astype(str)
    return work[(work["trade_date"] >= str(start)) & (work["trade_date"] <= str(end))]


def _params_from_json(params_json: str) -> dict:
    try:
        return json.loads(params_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _result_row(window: dict, best_params: dict, train_summary: dict, test_summary: dict) -> dict:
    train_return = float(train_summary.get("total_return", 0) or 0)
    test_return = float(test_summary.get("total_return", 0) or 0)
    train_drawdown = float(train_summary.get("max_drawdown", 0) or 0)
    test_drawdown = float(test_summary.get("max_drawdown", 0) or 0)
    train_pf = float(train_summary.get("profit_factor", 0) or 0)
    test_pf = float(test_summary.get("profit_factor", 0) or 0)
    train_trades = int(train_summary.get("trades_count", train_summary.get("turnover", 0)) or 0)
    test_trades = int(test_summary.get("trades_count", test_summary.get("turnover", 0)) or 0)
    overfit = bool(train_return > 0 and (test_return < 0 or test_return < train_return * 0.30))
    turnover_warning = bool(float(test_summary.get("turnover", test_trades) or 0) > 250)
    drawdown_warning = bool(abs(test_drawdown) > 0.20)
    return {
        **window,
        "best_params_json": json.dumps(best_params, ensure_ascii=False, sort_keys=True),
        "train_return": train_return,
        "test_return": test_return,
        "train_drawdown": train_drawdown,
        "test_drawdown": test_drawdown,
        "train_profit_factor": train_pf,
        "test_profit_factor": test_pf,
        "train_trades": train_trades,
        "test_trades": test_trades,
        "test_positive": bool(test_return > 0),
        "overfitting_flag": overfit,
        "turnover_warning": turnover_warning,
        "drawdown_warning": drawdown_warning,
        "metadata_json": json.dumps({"paper_rules": "walk_forward"}, ensure_ascii=False),
    }


def run_paper_walk_forward(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    train_months: int = 2,
    test_months: int = 1,
    param_grid: dict | None = None,
    objective: str = "total_return",
    capital: float = 100_000,
) -> pd.DataFrame:
    if prices_df is None or prices_df.empty or "trade_date" not in prices_df.columns:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    dates = pd.to_datetime(prices_df["trade_date"], errors="coerce").dropna()
    if dates.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    windows = create_paper_walk_forward_windows(dates.min().date().isoformat(), dates.max().date().isoformat(), train_months, test_months)
    rows = []
    for _, window in windows.iterrows():
        w = window.to_dict()
        train_signals = _slice(signals_df, w["train_start"], w["train_end"])
        train_prices = _slice(prices_df, w["train_start"], w["train_end"])
        train_risk = _slice(risk_df, w["train_start"], w["train_end"]) if risk_df is not None and not risk_df.empty else risk_df
        test_signals = _slice(signals_df, w["test_start"], w["test_end"])
        test_prices = _slice(prices_df, w["test_start"], w["test_end"])
        test_risk = _slice(risk_df, w["test_start"], w["test_end"]) if risk_df is not None and not risk_df.empty else risk_df
        train_opt = grid_search_exit_parameters(train_signals, train_prices, train_risk, param_grid=param_grid, objective=objective, capital=capital)
        ranked = rank_exit_parameter_results(train_opt)
        if ranked.empty:
            rows.append(_result_row(w, {}, {}, {}))
            continue
        best = ranked.iloc[0]
        params = _params_from_json(best.get("params_json"))
        test = run_paper_simulation(
            test_signals,
            test_prices,
            risk_df=test_risk,
            capital=capital,
            max_positions=int(params.get("max_positions", 5) or 5),
            risk_pct=float(params.get("risk_pct", 0.005) or 0.005),
            stop_loss_pct=params.get("stop_loss_pct"),
            take_profit_pct=params.get("take_profit_pct"),
            trailing_stop_pct=params.get("trailing_stop_pct"),
            atr_stop_multiplier=params.get("atr_stop_multiplier"),
            daily_loss_limit_pct=params.get("daily_loss_limit_pct"),
        )
        rows.append(_result_row(w, params, best.to_dict(), test["performance_summary"]))
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def summarize_paper_walk_forward(results_df: pd.DataFrame) -> dict:
    if results_df is None or results_df.empty:
        return {
            "windows_count": 0,
            "positive_windows_pct": 0.0,
            "mean_test_return": 0.0,
            "mean_test_drawdown": 0.0,
            "mean_test_profit_factor": 0.0,
            "avg_test_trades": 0.0,
            "overfitting_windows_pct": 0.0,
            "robustness_class": "PAPER_WF_DADOS_INSUFICIENTES",
        }
    df = results_df.copy()
    windows = len(df)
    positive_pct = float(df["test_positive"].fillna(False).mean()) if windows else 0.0
    overfit_pct = float(df["overfitting_flag"].fillna(False).mean()) if windows else 0.0
    mean_return = float(pd.to_numeric(df["test_return"], errors="coerce").fillna(0).mean())
    mean_drawdown = float(pd.to_numeric(df["test_drawdown"], errors="coerce").fillna(0).mean())
    mean_pf = float(pd.to_numeric(df["test_profit_factor"], errors="coerce").fillna(0).mean())
    avg_trades = float(pd.to_numeric(df["test_trades"], errors="coerce").fillna(0).mean())
    if windows < 2 or avg_trades < 5:
        robustness = "PAPER_WF_DADOS_INSUFICIENTES"
    elif overfit_pct >= 0.40:
        robustness = "PAPER_WF_OVERFIT_PROVAVEL"
    elif positive_pct >= 0.60 and mean_return > 0 and abs(mean_drawdown) <= 0.15:
        robustness = "PAPER_WF_ROBUSTO"
    elif positive_pct >= 0.50 and mean_return > 0:
        robustness = "PAPER_WF_PROMISSOR"
    else:
        robustness = "PAPER_WF_FRAGIL"
    return {
        "windows_count": int(windows),
        "positive_windows_pct": round(positive_pct, 4),
        "mean_test_return": round(mean_return, 6),
        "mean_test_drawdown": round(mean_drawdown, 6),
        "mean_test_profit_factor": round(mean_pf, 6),
        "avg_test_trades": round(avg_trades, 2),
        "overfitting_windows_pct": round(overfit_pct, 4),
        "robustness_class": robustness,
    }
