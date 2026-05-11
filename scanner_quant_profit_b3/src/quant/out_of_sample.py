"""Validação fora da amostra para sinais historicos do score quantitativo."""
from __future__ import annotations

import pandas as pd


def split_train_test_by_date(df: pd.DataFrame, train_end_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    data = df.copy()
    data["_trade_date"] = pd.to_datetime(data["trade_date"], errors="coerce")
    cutoff = pd.to_datetime(train_end_date)
    train = data[data["_trade_date"] <= cutoff].drop(columns=["_trade_date"]).reset_index(drop=True)
    test = data[data["_trade_date"] > cutoff].drop(columns=["_trade_date"]).reset_index(drop=True)
    return train, test


def _return_cols(df: pd.DataFrame) -> list[str]:
    return sorted(
        [col for col in df.columns if col.startswith("future_return_")],
        key=lambda col: int(col.replace("future_return_", "").replace("d", "")),
    )


def _payoff(returns: pd.Series) -> float:
    gains = returns[returns > 0]
    losses = returns[returns < 0].abs()
    if gains.empty or losses.empty:
        return 0.0
    return round(float(gains.mean() / losses.mean()), 4)


def _group_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()
    rows = []
    for value, group in df.groupby(group_col, dropna=False):
        row = {group_col: value, "signals": int(len(group))}
        for ret_col in _return_cols(group):
            suffix = ret_col.replace("future_return_", "")
            returns = pd.to_numeric(group[ret_col], errors="coerce").dropna()
            row[f"mean_return_{suffix}"] = round(float(returns.mean()), 4) if not returns.empty else 0.0
            row[f"hit_rate_{suffix}"] = round(float((returns > 0).mean()), 4) if not returns.empty else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def _summary(df: pd.DataFrame) -> dict:
    summary: dict = {
        "signals": int(len(df)) if df is not None else 0,
        "by_signal_type": pd.DataFrame(),
        "by_score_bucket": pd.DataFrame(),
    }
    if df is None or df.empty:
        return summary

    for ret_col in _return_cols(df):
        suffix = ret_col.replace("future_return_", "")
        returns = pd.to_numeric(df[ret_col], errors="coerce").dropna()
        summary[f"mean_return_{suffix}"] = round(float(returns.mean()), 4) if not returns.empty else 0.0
        summary[f"median_return_{suffix}"] = round(float(returns.median()), 4) if not returns.empty else 0.0
        summary[f"hit_rate_{suffix}"] = round(float((returns > 0).mean()), 4) if not returns.empty else 0.0
        summary[f"best_return_{suffix}"] = round(float(returns.max()), 4) if not returns.empty else 0.0
        summary[f"worst_return_{suffix}"] = round(float(returns.min()), 4) if not returns.empty else 0.0
        summary[f"std_return_{suffix}"] = round(float(returns.std(ddof=0)), 4) if not returns.empty else 0.0
        summary[f"payoff_{suffix}"] = _payoff(returns)

    summary["by_signal_type"] = _group_summary(df, "signal_type")
    summary["by_score_bucket"] = _group_summary(df, "score_bucket")
    return summary


def evaluate_train_test_performance(backtest_df: pd.DataFrame, train_end_date: str) -> dict:
    train, test = split_train_test_by_date(backtest_df, train_end_date)
    return {
        "train": _summary(train),
        "test": _summary(test),
        "train_df": train,
        "test_df": test,
    }


def _best_group(summary: dict, table_key: str, group_col: str, metric: str) -> str | None:
    table = summary.get(table_key)
    if table is None or table.empty or metric not in table.columns:
        return None
    return str(table.sort_values(metric, ascending=False).iloc[0][group_col])


def compare_train_test(train_summary: dict, test_summary: dict, horizon: int = 5) -> dict:
    metric = f"mean_return_{horizon}d"
    train_return = float(train_summary.get(metric, 0.0) or 0.0)
    test_return = float(test_summary.get(metric, 0.0) or 0.0)
    degradation = train_return - test_return
    performance_degraded = test_return < train_return * 0.5 if train_return > 0 else test_return < train_return

    best_train_signal = _best_group(train_summary, "by_signal_type", "signal_type", metric)
    best_test_signal = _best_group(test_summary, "by_signal_type", "signal_type", metric)
    best_train_bucket = _best_group(train_summary, "by_score_bucket", "score_bucket", metric)
    best_test_bucket = _best_group(test_summary, "by_score_bucket", "score_bucket", metric)
    insufficient = train_summary.get("signals", 0) < 30 or test_summary.get("signals", 0) < 30
    overfitting = bool(performance_degraded)
    if performance_degraded:
        diagnosis = "A performance caiu fora da amostra; há indício de overfitting se a amostra for suficiente."
    else:
        diagnosis = "A performance fora da amostra ficou próxima do treino."

    return {
        "train_return": round(train_return, 4),
        "test_return": round(test_return, 4),
        "degradation": round(float(degradation), 4),
        "performance_degraded": bool(performance_degraded),
        "best_train_signal_type": best_train_signal,
        "best_test_signal_type": best_test_signal,
        "signal_type_stable": best_train_signal == best_test_signal and best_train_signal is not None,
        "best_train_score_bucket": best_train_bucket,
        "best_test_score_bucket": best_test_bucket,
        "score_bucket_stable": best_train_bucket == best_test_bucket and best_train_bucket is not None,
        "insufficient_sample": bool(insufficient),
        "overfitting_alert": overfitting,
        "diagnosis": diagnosis,
    }
