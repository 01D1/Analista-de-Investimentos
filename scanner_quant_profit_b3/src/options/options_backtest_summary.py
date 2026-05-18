"""Resumos e relatório textual do backtest preliminar de estruturas de opções."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _rate(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return round(float((values > 0).mean() * 100), 4) if not values.empty else 0.0


def _numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[column], errors="coerce")


def _date_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df[column], errors="coerce")


def summarize_structure_backtest(results_df: pd.DataFrame) -> dict[str, Any]:
    if results_df is None or results_df.empty:
        return {
            "total_trades": 0,
            "completed_count": 0,
            "skipped_count": 0,
            "win_rate": 0.0,
            "mean_net_return": 0.0,
            "median_net_return": 0.0,
            "mean_return_on_risk": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "payoff_ratio": 0.0,
            "profit_factor": 0.0,
            "avg_cost_drag": 0.0,
            "avg_spread_cost": 0.0,
            "avg_slippage_cost": 0.0,
            "avg_dte_entry": 0.0,
            "avg_holding_days": 0.0,
        }
    df = results_df.copy()
    completed = df[df["status"].astype(str) == "COMPLETED"] if "status" in df.columns else df
    returns = pd.to_numeric(completed.get("net_return"), errors="coerce")
    pnl = pd.to_numeric(completed.get("net_pnl"), errors="coerce")
    gains = pnl[pnl > 0].sum()
    losses = abs(pnl[pnl < 0].sum())
    cost_drag = _numeric_column(completed, "transaction_cost").fillna(0) + _numeric_column(completed, "slippage_cost").fillna(0)
    entry_dates = _date_column(completed, "entry_date")
    exit_dates = _date_column(completed, "exit_date")
    holding = (exit_dates - entry_dates).dt.days
    return {
        "total_trades": int(len(df)),
        "completed_count": int(len(completed)),
        "skipped_count": int(len(df) - len(completed)),
        "win_rate": _rate(completed.get("net_pnl", pd.Series(dtype=float))),
        "mean_net_return": round(float(returns.mean()), 6) if returns.notna().any() else 0.0,
        "median_net_return": round(float(returns.median()), 6) if returns.notna().any() else 0.0,
        "mean_return_on_risk": round(float(_numeric_column(completed, "return_on_risk").mean()), 6) if len(completed) else 0.0,
        "best_trade": round(float(returns.max()), 6) if returns.notna().any() else 0.0,
        "worst_trade": round(float(returns.min()), 6) if returns.notna().any() else 0.0,
        "payoff_ratio": round(float(completed.loc[pnl > 0, "net_pnl"].mean() / abs(completed.loc[pnl < 0, "net_pnl"].mean())), 6) if (pnl > 0).any() and (pnl < 0).any() else 0.0,
        "profit_factor": round(float(gains / losses), 6) if losses else (999.0 if gains > 0 else 0.0),
        "avg_cost_drag": round(float(cost_drag.mean()), 6) if len(cost_drag) else 0.0,
        "avg_spread_cost": round(float(_numeric_column(completed, "spread_cost").mean()), 6) if len(completed) else 0.0,
        "avg_slippage_cost": round(float(_numeric_column(completed, "slippage_cost").mean()), 6) if len(completed) else 0.0,
        "avg_dte_entry": round(float(_numeric_column(completed, "dte_entry").mean()), 2) if len(completed) else 0.0,
        "avg_holding_days": round(float(holding.mean()), 2) if holding.notna().any() else 0.0,
    }


def summarize_by_structure_type(results_df: pd.DataFrame) -> pd.DataFrame:
    return _group_summary(results_df, "structure_type")


def summarize_by_underlying(results_df: pd.DataFrame) -> pd.DataFrame:
    return _group_summary(results_df, "underlying")


def summarize_by_regime(results_df: pd.DataFrame, regimes_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if regimes_df is None or regimes_df.empty or results_df is None or results_df.empty:
        return pd.DataFrame(columns=["primary_regime", "trades", "mean_net_return", "win_rate"])
    merged = results_df.merge(regimes_df[["trade_date", "primary_regime"]], left_on="entry_date", right_on="trade_date", how="left")
    return _group_summary(merged, "primary_regime")


def summarize_by_event_context(results_df: pd.DataFrame, events_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if events_df is None or events_df.empty or results_df is None or results_df.empty:
        return pd.DataFrame(columns=["has_event", "trades", "mean_net_return", "win_rate"])
    events = events_df[["event_date", "ticker"]].drop_duplicates()
    merged = results_df.merge(events, left_on=["entry_date", "underlying"], right_on=["event_date", "ticker"], how="left")
    merged["has_event"] = merged["event_date"].notna()
    return _group_summary(merged, "has_event")


def split_options_train_test_by_date(results_df: pd.DataFrame, train_end_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if results_df is None or results_df.empty:
        empty = pd.DataFrame(columns=getattr(results_df, "columns", []))
        return empty, empty
    dates = pd.to_datetime(results_df.get("entry_date"), errors="coerce")
    cutoff = pd.Timestamp(train_end_date)
    train = results_df[dates <= cutoff].copy()
    test = results_df[dates > cutoff].copy()
    return train.reset_index(drop=True), test.reset_index(drop=True)


def evaluate_options_out_of_sample(results_df: pd.DataFrame, train_end_date: str) -> dict[str, Any]:
    train, test = split_options_train_test_by_date(results_df, train_end_date)
    train_summary = summarize_structure_backtest(train)
    test_summary = summarize_structure_backtest(test)
    degradation = round(float(train_summary.get("mean_net_return", 0) - test_summary.get("mean_net_return", 0)), 6)
    if test_summary["completed_count"] == 0:
        status = "OOS_SEM_AMOSTRA"
    elif train_summary["mean_net_return"] > 0 and test_summary["mean_net_return"] <= 0:
        status = "OOS_FRAGIL"
    elif test_summary["mean_net_return"] > 0 and test_summary["win_rate"] >= 50:
        status = "OOS_PROMISSOR"
    else:
        status = "OOS_EM_OBSERVACAO"
    return {
        "train": train_summary,
        "test": test_summary,
        "degradation": degradation,
        "oos_status": status,
        "train_end_date": train_end_date,
    }


def _group_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    columns = [group_col, "trades", "completed", "mean_net_return", "win_rate", "profit_factor"]
    if df is None or df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for value, group in df.groupby(group_col, dropna=False):
        summary = summarize_structure_backtest(group)
        rows.append(
            {
                group_col: value,
                "trades": summary["total_trades"],
                "completed": summary["completed_count"],
                "mean_net_return": summary["mean_net_return"],
                "win_rate": summary["win_rate"],
                "profit_factor": summary["profit_factor"],
            }
        )
    return pd.DataFrame(rows, columns=columns)


def generate_options_backtest_report(summary: dict[str, Any]) -> str:
    total = int(summary.get("total_trades") or 0)
    completed = int(summary.get("completed_count") or 0)
    if total <= 0:
        return "Backtest preliminar de opções sem amostra. Não há dados históricos suficientes para conclusão."
    return (
        "Backtest preliminar de opções. Resultados dependem da qualidade da cadeia histórica, bid/ask e premissas de execução. "
        "Não constitui recomendação. "
        f"Foram avaliadas {total} entradas, com {completed} concluídas, win rate de {summary.get('win_rate', 0)}%, "
        f"retorno líquido médio de {summary.get('mean_net_return', 0)}% e profit factor de {summary.get('profit_factor', 0)}."
    )
