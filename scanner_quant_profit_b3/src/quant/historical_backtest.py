"""Backtest historico diario para score_final e tipos de sinal."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def score_bucket(score: float) -> str:
    if score < 20:
        return "0_20"
    if score < 40:
        return "20_40"
    if score < 60:
        return "40_60"
    if score < 80:
        return "60_80"
    return "80_100"


def run_historical_backtest(
    features_scores_df: pd.DataFrame,
    horizons: Iterable[int] = (1, 3, 5, 10),
) -> pd.DataFrame:
    if features_scores_df is None or features_scores_df.empty:
        return pd.DataFrame()

    horizons = tuple(int(h) for h in horizons)
    df = features_scores_df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df = df.dropna(subset=["trade_date", "ticker", "close", "score_final"])
    for col in ["open", "high", "low", "close", "score_final"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values(["ticker", "trade_date"]).reset_index(drop=True)

    rows = []
    for _, group in df.groupby("ticker", sort=False):
        g = group.reset_index(drop=True).copy()
        for horizon in horizons:
            g[f"future_return_{horizon}d"] = (g["close"].shift(-horizon) / g["close"] - 1.0) * 100.0
            g[f"hit_{horizon}d"] = g[f"future_return_{horizon}d"] > 0

        future_highs = []
        future_lows = []
        for idx in range(len(g)):
            window = g.iloc[idx + 1 : idx + 6]
            if window.empty:
                future_highs.append(np.nan)
                future_lows.append(np.nan)
            else:
                future_highs.append(window["high"].max() if "high" in window else window["close"].max())
                future_lows.append(window["low"].min() if "low" in window else window["close"].min())
        g["max_favorable_excursion_5d"] = (pd.Series(future_highs) / g["close"] - 1.0) * 100.0
        g["max_adverse_excursion_5d"] = (pd.Series(future_lows) / g["close"] - 1.0) * 100.0
        rows.append(g)

    out = pd.concat(rows, ignore_index=True)
    out["score_bucket"] = out["score_final"].apply(lambda value: score_bucket(float(value)))
    numeric_cols = out.select_dtypes(include=["number"]).columns
    out[numeric_cols] = out[numeric_cols].replace([np.inf, -np.inf], np.nan).round(4)
    out["trade_date"] = out["trade_date"].dt.date.astype(str)

    return out.dropna(subset=[f"future_return_{h}d" for h in horizons], how="all").reset_index(drop=True)


def _payoff(returns: pd.Series) -> float:
    gains = returns[returns > 0]
    losses = returns[returns < 0].abs()
    if gains.empty or losses.empty:
        return 0.0
    return round(float(gains.mean() / losses.mean()), 4)


def _summary(df: pd.DataFrame, group_col: str, min_samples: int = 1) -> pd.DataFrame:
    if df is None or df.empty or group_col not in df.columns:
        return pd.DataFrame()

    horizons = sorted(
        int(col.replace("future_return_", "").replace("d", ""))
        for col in df.columns
        if col.startswith("future_return_")
    )
    rows = []
    for value, group in df.groupby(group_col):
        row = {group_col: value, "signals": int(len(group)), "min_sample_ok": bool(len(group) >= min_samples)}
        for horizon in horizons:
            ret_col = f"future_return_{horizon}d"
            hit_col = f"hit_{horizon}d"
            returns = pd.to_numeric(group[ret_col], errors="coerce").dropna()
            row[f"mean_return_{horizon}d"] = round(float(returns.mean()), 4) if not returns.empty else 0.0
            row[f"median_return_{horizon}d"] = round(float(returns.median()), 4) if not returns.empty else 0.0
            row[f"hit_rate_{horizon}d"] = round(float(group.loc[returns.index, hit_col].mean()), 4) if not returns.empty else 0.0
            row[f"best_return_{horizon}d"] = round(float(returns.max()), 4) if not returns.empty else 0.0
            row[f"worst_return_{horizon}d"] = round(float(returns.min()), 4) if not returns.empty else 0.0
            row[f"std_return_{horizon}d"] = round(float(returns.std(ddof=0)), 4) if not returns.empty else 0.0
            row[f"payoff_{horizon}d"] = _payoff(returns)
        rows.append(row)

    return pd.DataFrame(rows)


def summarize_backtest_by_signal_type(backtest_df: pd.DataFrame, min_samples: int = 1) -> pd.DataFrame:
    return _summary(backtest_df, "signal_type", min_samples=min_samples)


def summarize_backtest_by_score_bucket(backtest_df: pd.DataFrame, min_samples: int = 1) -> pd.DataFrame:
    return _summary(backtest_df, "score_bucket", min_samples=min_samples)


def summarize_backtest_by_component_quantile(
    backtest_df: pd.DataFrame,
    components: Iterable[str] = (
        "score_momentum",
        "score_tendencia",
        "score_liquidez",
        "score_volatilidade",
        "score_risco",
    ),
    quantiles: int = 5,
) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame()

    rows = []
    for component in components:
        if component not in backtest_df.columns:
            continue
        values = pd.to_numeric(backtest_df[component], errors="coerce")
        if values.dropna().nunique() < 2:
            continue
        labels = [f"Q{i + 1}" for i in range(min(quantiles, values.dropna().nunique()))]
        buckets = pd.qcut(values.rank(method="first"), q=len(labels), labels=labels, duplicates="drop")
        tmp = backtest_df.copy()
        tmp["component_quantile"] = buckets.astype(str)
        for quantile, group in tmp.groupby("component_quantile"):
            returns = pd.to_numeric(group.get("future_return_5d"), errors="coerce").dropna()
            rows.append(
                {
                    "component": component,
                    "quantile": quantile,
                    "signals": int(len(group)),
                    "mean_return_5d": round(float(returns.mean()), 4) if not returns.empty else 0.0,
                    "hit_rate_5d": round(float(group.loc[returns.index, "hit_5d"].mean()), 4)
                    if not returns.empty and "hit_5d" in group
                    else 0.0,
                }
            )

    return pd.DataFrame(rows)


def generate_historical_backtest_report(
    summary_by_signal: pd.DataFrame,
    summary_by_bucket: pd.DataFrame,
    calibration_suggestions: str | None = None,
) -> str:
    total = int(summary_by_signal["signals"].sum()) if summary_by_signal is not None and not summary_by_signal.empty else 0
    text = f"Foram analisados {total} sinais no backtest historico."

    if summary_by_signal is not None and not summary_by_signal.empty:
        mean_cols = [c for c in summary_by_signal.columns if c.startswith("mean_return_")]
        hit_cols = [c for c in summary_by_signal.columns if c.startswith("hit_rate_")]
        if mean_cols:
            best = summary_by_signal.sort_values(mean_cols[-1], ascending=False).iloc[0]
            text += f" O tipo de sinal com melhor retorno medio em {mean_cols[-1].replace('mean_return_', 'D+')} foi {best['signal_type']}."
        if hit_cols:
            best_hit = summary_by_signal.sort_values(hit_cols[-1], ascending=False).iloc[0]
            text += f" A melhor taxa de acerto em {hit_cols[-1].replace('hit_rate_', 'D+')} apareceu em {best_hit['signal_type']}."

    if summary_by_bucket is not None and not summary_by_bucket.empty:
        mean_cols = [c for c in summary_by_bucket.columns if c.startswith("mean_return_")]
        if mean_cols:
            best_bucket = summary_by_bucket.sort_values(mean_cols[-1], ascending=False).iloc[0]
            text += f" A faixa de score_final com melhor desempenho foi {best_bucket['score_bucket']}."

    if calibration_suggestions:
        text += " " + calibration_suggestions
    return text
