"""Walk-forward fora da amostra para estruturas de opções."""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.options.options_backtest_summary import summarize_structure_backtest
from src.options.structure_backtest import run_structure_backtest


WF_COLUMNS = [
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "train_trades",
    "test_trades",
    "train_mean_net_return",
    "test_mean_net_return",
    "train_win_rate",
    "test_win_rate",
    "train_profit_factor",
    "test_profit_factor",
    "avg_cost_drag",
    "skipped_pct",
    "positive_test_window",
    "overfitting_flag",
    "insufficient_data_flag",
    "metadata_json",
]


def create_options_walk_forward_windows(start_date: str, end_date: str, train_months: int = 3, test_months: int = 1) -> pd.DataFrame:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    rows = []
    current = start
    window_id = 1
    while current < end:
        train_start = current
        train_end = train_start + pd.DateOffset(months=int(train_months)) - pd.Timedelta(days=1)
        test_start = train_end + pd.Timedelta(days=1)
        test_end = test_start + pd.DateOffset(months=int(test_months)) - pd.Timedelta(days=1)
        if test_start > end:
            break
        rows.append(
            {
                "window_id": window_id,
                "train_start": str(train_start.date()),
                "train_end": str(min(train_end, end).date()),
                "test_start": str(test_start.date()),
                "test_end": str(min(test_end, end).date()),
            }
        )
        current = test_start
        window_id += 1
    return pd.DataFrame(rows, columns=["window_id", "train_start", "train_end", "test_start", "test_end"])


def _slice_chain(chain_df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if chain_df is None or chain_df.empty:
        return pd.DataFrame()
    dates = pd.to_datetime(chain_df["trade_date"], errors="coerce")
    return chain_df[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))].copy()


def _row_for_window(window: pd.Series, train_summary: dict[str, Any], test_summary: dict[str, Any]) -> dict[str, Any]:
    skipped_pct = test_summary["skipped_count"] / test_summary["total_trades"] * 100 if test_summary["total_trades"] else 100.0
    insufficient = train_summary["completed_count"] == 0 or test_summary["completed_count"] == 0
    overfit = train_summary["mean_net_return"] > 0 and test_summary["mean_net_return"] <= 0
    return {
        "window_id": int(window["window_id"]),
        "train_start": window["train_start"],
        "train_end": window["train_end"],
        "test_start": window["test_start"],
        "test_end": window["test_end"],
        "train_trades": train_summary["total_trades"],
        "test_trades": test_summary["total_trades"],
        "train_mean_net_return": train_summary["mean_net_return"],
        "test_mean_net_return": test_summary["mean_net_return"],
        "train_win_rate": train_summary["win_rate"],
        "test_win_rate": test_summary["win_rate"],
        "train_profit_factor": train_summary["profit_factor"],
        "test_profit_factor": test_summary["profit_factor"],
        "avg_cost_drag": test_summary["avg_cost_drag"],
        "skipped_pct": round(float(skipped_pct), 4),
        "positive_test_window": int(test_summary["mean_net_return"] > 0 and test_summary["completed_count"] > 0),
        "overfitting_flag": int(overfit),
        "insufficient_data_flag": int(insufficient),
        "metadata_json": "{}",
    }


def run_options_walk_forward(
    chain_df: pd.DataFrame,
    structure_type: str,
    rules: dict | None,
    exit_rules: dict | None,
    cost_model: dict | None,
    train_months: int = 3,
    test_months: int = 1,
) -> pd.DataFrame:
    if chain_df is None or chain_df.empty or "trade_date" not in chain_df.columns:
        return pd.DataFrame(columns=WF_COLUMNS)
    dates = pd.to_datetime(chain_df["trade_date"], errors="coerce").dropna()
    if dates.empty:
        return pd.DataFrame(columns=WF_COLUMNS)
    windows = create_options_walk_forward_windows(str(dates.min().date()), str(dates.max().date()), train_months, test_months)
    rows = []
    for _, window in windows.iterrows():
        train_chain = _slice_chain(chain_df, window["train_start"], window["train_end"])
        test_chain = _slice_chain(chain_df, window["test_start"], window["test_end"])
        train_results = run_structure_backtest(train_chain, structure_type, rules, exit_rules, cost_model)
        test_results = run_structure_backtest(test_chain, structure_type, rules, exit_rules, cost_model)
        rows.append(_row_for_window(window, summarize_structure_backtest(train_results), summarize_structure_backtest(test_results)))
    return pd.DataFrame(rows, columns=WF_COLUMNS)


def summarize_options_walk_forward(results_df: pd.DataFrame) -> dict[str, Any]:
    if results_df is None or results_df.empty:
        return {
            "windows_count": 0,
            "positive_windows_pct": 0.0,
            "mean_test_net_return": 0.0,
            "mean_test_win_rate": 0.0,
            "mean_test_profit_factor": 0.0,
            "avg_test_trades": 0.0,
            "insufficient_windows_count": 0,
            "overfitting_windows_count": 0,
            "robustness_class": "OPTIONS_WF_DADOS_INSUFICIENTES",
        }
    df = results_df.copy()
    windows = len(df)
    insufficient = int(pd.to_numeric(df["insufficient_data_flag"], errors="coerce").fillna(0).sum())
    overfit = int(pd.to_numeric(df["overfitting_flag"], errors="coerce").fillna(0).sum())
    positive_pct = round(float(pd.to_numeric(df["positive_test_window"], errors="coerce").fillna(0).mean() * 100), 4)
    mean_return = round(float(pd.to_numeric(df["test_mean_net_return"], errors="coerce").mean()), 6)
    mean_win = round(float(pd.to_numeric(df["test_win_rate"], errors="coerce").mean()), 4)
    avg_trades = round(float(pd.to_numeric(df["test_trades"], errors="coerce").mean()), 2)
    if windows < 2 or insufficient == windows or avg_trades <= 0:
        klass = "OPTIONS_WF_DADOS_INSUFICIENTES"
    elif overfit / windows >= 0.5:
        klass = "OPTIONS_WF_OVERFIT_PROVAVEL"
    elif positive_pct >= 60 and mean_return > 0 and mean_win >= 52:
        klass = "OPTIONS_WF_ROBUSTO"
    elif positive_pct >= 50 and mean_return > 0:
        klass = "OPTIONS_WF_PROMISSOR"
    else:
        klass = "OPTIONS_WF_FRAGIL"
    return {
        "windows_count": int(windows),
        "positive_windows_pct": positive_pct,
        "mean_test_net_return": mean_return,
        "mean_test_win_rate": mean_win,
        "mean_test_profit_factor": round(float(pd.to_numeric(df["test_profit_factor"], errors="coerce").replace(999.0, pd.NA).mean()), 6) if windows else 0.0,
        "avg_test_trades": avg_trades,
        "insufficient_windows_count": insufficient,
        "overfitting_windows_count": overfit,
        "robustness_class": klass,
    }


def generate_options_walk_forward_report(summary: dict[str, Any], results_df: pd.DataFrame) -> str:
    windows = int(summary.get("windows_count") or 0)
    if windows == 0 or summary.get("robustness_class") == "OPTIONS_WF_DADOS_INSUFICIENTES":
        return "Walk-forward de opções sem amostra suficiente. Resultado ainda insuficiente para aprovação por baixa cobertura histórica de cadeia."
    return (
        f"Walk-forward de opções executado em {windows} janelas. "
        f"Janelas positivas: {summary.get('positive_windows_pct', 0)}%. "
        f"Retorno líquido médio de teste: {summary.get('mean_test_net_return', 0)}%. "
        f"Robustez: {summary.get('robustness_class')}. Não constitui recomendação."
    )

