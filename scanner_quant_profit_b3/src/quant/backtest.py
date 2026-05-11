"""Backtest estatístico simples de sinais, sem simular execução real."""
from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def evaluate_forward_returns(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    horizons: Iterable[int] = (1, 3, 5, 10),
) -> pd.DataFrame:
    price_df = prices.copy()
    signal_df = signals.copy()
    price_df["trade_date"] = pd.to_datetime(price_df["trade_date"])
    signal_df["signal_date"] = pd.to_datetime(signal_df["signal_date"])
    horizons = tuple(horizons)

    rows: list[dict] = []
    for _, signal in signal_df.iterrows():
        ticker = signal["ticker"]
        entry = float(signal.get("entry_price") or 0)
        if entry <= 0:
            continue

        series = (
            price_df[(price_df["ticker"] == ticker) & (price_df["trade_date"] >= signal["signal_date"])]
            .sort_values("trade_date")
            .reset_index(drop=True)
        )
        if series.empty:
            continue

        closes = pd.to_numeric(series["close"], errors="coerce")
        for horizon in horizons:
            if len(closes) <= horizon:
                continue
            window = closes.iloc[: horizon + 1]
            future_return = (window.iloc[-1] / entry - 1.0) * 100.0
            mfe = (window.max() / entry - 1.0) * 100.0
            mae = (window.min() / entry - 1.0) * 100.0
            rows.append(
                {
                    "signal_id": signal.get("signal_id"),
                    "ticker": ticker,
                    "signal_date": signal["signal_date"].date().isoformat(),
                    "signal_type": signal.get("signal_type"),
                    "score_final": signal.get("score_final"),
                    "horizon": horizon,
                    "future_return": round(future_return, 4),
                    "max_favorable_excursion": round(mfe, 4),
                    "max_adverse_excursion": round(mae, 4),
                    "hit": bool(future_return > 0),
                }
            )

    return pd.DataFrame(rows)
