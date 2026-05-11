"""Backtest estatístico por divergência e faixa de score."""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def _signal_date_column(df: pd.DataFrame) -> str:
    if "signal_date" in df.columns:
        return "signal_date"
    if "captured_at" in df.columns:
        return "captured_at"
    raise KeyError("signals_df precisa de signal_date ou captured_at")


def _asset_column(df: pd.DataFrame) -> str:
    if "asset" in df.columns:
        return "asset"
    if "ticker" in df.columns:
        return "ticker"
    raise KeyError("signals_df precisa de asset ou ticker")


def _bucket(score: float) -> str:
    if score < 20:
        return "0_20"
    if score < 40:
        return "20_40"
    if score < 60:
        return "40_60"
    if score < 80:
        return "60_80"
    return "80_100"


def calculate_forward_returns(
    signals_df: pd.DataFrame,
    daily_prices_df: pd.DataFrame,
    horizons: Iterable[int] = (1, 3, 5, 10),
) -> pd.DataFrame:
    if signals_df is None or signals_df.empty or daily_prices_df is None or daily_prices_df.empty:
        return pd.DataFrame()

    date_col = _signal_date_column(signals_df)
    asset_col = _asset_column(signals_df)
    signals = signals_df.copy()
    prices = daily_prices_df.copy()
    signals["_signal_date"] = pd.to_datetime(signals[date_col], errors="coerce").dt.normalize()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"], errors="coerce").dt.normalize()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    horizons = tuple(horizons)

    rows = []
    for _, signal in signals.iterrows():
        asset = signal[asset_col]
        series = (
            prices[(prices["ticker"] == asset) & (prices["trade_date"] >= signal["_signal_date"])]
            .sort_values("trade_date")
            .reset_index(drop=True)
        )
        if len(series) < 2:
            continue
        entry = float(series.loc[0, "close"])
        if entry <= 0:
            continue

        for horizon in horizons:
            if len(series) <= horizon:
                continue
            window = series.iloc[: horizon + 1]
            exit_close = float(window.iloc[-1]["close"])
            future_return = (exit_close / entry - 1.0) * 100.0
            mfe = (window["close"].max() / entry - 1.0) * 100.0
            mae = (window["close"].min() / entry - 1.0) * 100.0
            score_final = float(signal.get("score_final", 0) or 0)
            rows.append(
                {
                    "signal_id": signal.get("signal_id", signal.get("id")),
                    "asset": asset,
                    "signal_date": signal["_signal_date"].date().isoformat(),
                    "horizon": int(horizon),
                    "score_final": round(score_final, 4),
                    "score_bucket": _bucket(score_final),
                    "divergence_type": signal.get("divergence_type", "INDEFINIDO"),
                    "future_return": round(future_return, 4),
                    "max_favorable_excursion": round(mfe, 4),
                    "max_adverse_excursion": round(mae, 4),
                    "hit": bool(future_return > 0),
                }
            )

    return pd.DataFrame(rows)


def _wide_summary(backtest_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame()

    rows = []
    for group_value, group_df in backtest_df.groupby(group_col):
        row = {group_col: group_value, "signals": int(group_df["asset"].nunique())}
        for horizon, hdf in group_df.groupby("horizon"):
            suffix = f"d{int(horizon)}"
            returns = pd.to_numeric(hdf["future_return"], errors="coerce").dropna()
            row[f"mean_return_{suffix}"] = round(float(returns.mean()), 4) if not returns.empty else 0.0
            row[f"median_return_{suffix}"] = round(float(returns.median()), 4) if not returns.empty else 0.0
            row[f"hit_rate_{suffix}"] = round(float(hdf["hit"].mean()), 4) if not hdf.empty else 0.0
            row[f"best_return_{suffix}"] = round(float(returns.max()), 4) if not returns.empty else 0.0
            row[f"worst_return_{suffix}"] = round(float(returns.min()), 4) if not returns.empty else 0.0
            row[f"std_return_{suffix}"] = round(float(returns.std(ddof=0)), 4) if not returns.empty else 0.0
            gains = returns[returns > 0]
            losses = returns[returns < 0].abs()
            row[f"payoff_{suffix}"] = round(float(gains.mean() / losses.mean()), 4) if not gains.empty and not losses.empty else 0.0
        rows.append(row)

    return pd.DataFrame(rows)


def summarize_by_divergence(backtest_df: pd.DataFrame) -> pd.DataFrame:
    return _wide_summary(backtest_df, "divergence_type")


def summarize_by_score_bucket(backtest_df: pd.DataFrame) -> pd.DataFrame:
    return _wide_summary(backtest_df, "score_bucket")


def generate_calibration_report(
    history_df: pd.DataFrame,
    latest_run_df: pd.DataFrame,
    backtest_summary_df: pd.DataFrame | None = None,
) -> str:
    if history_df is None or history_df.empty:
        return "Sem histórico de calibração disponível."

    latest_history = history_df.iloc[-1]
    total = int(latest_history.get("total_assets", len(latest_run_df) if latest_run_df is not None else 0))
    mean_score = latest_history.get("mean_score_final", 0)
    count_high = int(latest_history.get("count_80_100", 0) or 0)
    inflation = bool(latest_history.get("inflation_alert", 0))
    inflation_text = "Houve alerta de inflação." if inflation else "Não houve alerta de inflação."

    dominant = "INDEFINIDO"
    if latest_run_df is not None and not latest_run_df.empty and "divergence_type" in latest_run_df.columns:
        dominant = str(latest_run_df["divergence_type"].value_counts().idxmax())

    text = (
        f"A última rodada analisou {total} ativos. A média do score_final foi {mean_score}, "
        f"com {count_high} ativos acima de 80. {inflation_text} "
        f"O tipo mais comum foi {dominant}."
    )

    if backtest_summary_df is not None and not backtest_summary_df.empty and "mean_return_d3" in backtest_summary_df.columns:
        best = backtest_summary_df.sort_values("mean_return_d3", ascending=False).iloc[0]
        text += (
            f" No histórico disponível, os sinais {best['divergence_type']} apresentaram melhor "
            f"retorno médio em D+3, mas a interpretação depende do tamanho da amostra."
        )

    return text
