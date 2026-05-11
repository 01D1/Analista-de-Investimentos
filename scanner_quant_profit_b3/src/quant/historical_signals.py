"""Features, scores e sinais quantitativos sobre historico diario."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .explanations import explain_signal
from .liquidity import liquidity_profile
from .scoring import score_asset
from .signals import classify_asset_signal


def _position_in_range(close: pd.Series, high: pd.Series, low: pd.Series) -> pd.Series:
    denom = high - low
    return ((close - low) / denom.replace(0, np.nan) * 100.0).clip(0, 100)


def _true_range(group: pd.DataFrame) -> pd.Series:
    prev_close = group["close"].shift(1)
    ranges = pd.concat(
        [
            group["high"] - group["low"],
            (group["high"] - prev_close).abs(),
            (group["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def generate_historical_features(daily_prices_df: pd.DataFrame) -> pd.DataFrame:
    if daily_prices_df is None or daily_prices_df.empty:
        return pd.DataFrame()

    df = daily_prices_df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    for col in ["open", "high", "low", "close", "volume", "trades", "quantity"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["trade_date", "ticker", "close"]).sort_values(["ticker", "trade_date"])

    pieces = []
    for _, group in df.groupby("ticker", sort=False):
        g = group.copy()
        prev_close = g["close"].shift(1)
        g["return_1d"] = g["close"].pct_change(1) * 100.0
        g["return_3d"] = g["close"].pct_change(3) * 100.0
        g["return_5d"] = g["close"].pct_change(5) * 100.0
        g["range_pct"] = (g["high"] - g["low"]) / prev_close.replace(0, np.nan) * 100.0
        g["gap_pct"] = (g["open"] / prev_close.replace(0, np.nan) - 1.0) * 100.0
        g["last_vs_open_pct"] = (g["close"] / g["open"].replace(0, np.nan) - 1.0) * 100.0
        g["position_range_pct"] = _position_in_range(g["close"], g["high"], g["low"])
        g["volume_ma_20"] = g["volume"].shift(1).rolling(20, min_periods=1).mean()
        g["trades_ma_20"] = g["trades"].shift(1).rolling(20, min_periods=1).mean()
        g["volume_relative_20"] = g["volume"] / g["volume_ma_20"].replace(0, np.nan)
        g["volatility_20"] = g["return_1d"].shift(1).rolling(20, min_periods=2).std(ddof=0)
        tr = _true_range(g)
        g["atr_14"] = tr.rolling(14, min_periods=1).mean()
        high_20 = g["high"].rolling(20, min_periods=1).max()
        low_20 = g["low"].rolling(20, min_periods=1).min()
        g["distance_from_high_20"] = (g["close"] / high_20.replace(0, np.nan) - 1.0) * 100.0
        g["distance_from_low_20"] = (g["close"] / low_20.replace(0, np.nan) - 1.0) * 100.0
        g["moving_average_9"] = g["close"].rolling(9, min_periods=1).mean()
        g["moving_average_21"] = g["close"].rolling(21, min_periods=1).mean()
        g["moving_average_50"] = g["close"].rolling(50, min_periods=1).mean()
        g["trend_short"] = np.select(
            [g["close"] > g["moving_average_9"], g["close"] < g["moving_average_9"]],
            ["ALTA", "BAIXA"],
            default="NEUTRA",
        )
        g["trend_medium"] = np.select(
            [g["moving_average_9"] > g["moving_average_21"], g["moving_average_9"] < g["moving_average_21"]],
            ["ALTA", "BAIXA"],
            default="NEUTRA",
        )
        pieces.append(g)

    out = pd.concat(pieces, ignore_index=True)
    universe_mean = out.groupby("trade_date")["return_5d"].transform("mean")
    out["relative_strength_vs_universe"] = out["return_5d"] - universe_mean
    numeric_cols = out.select_dtypes(include=["number"]).columns
    out[numeric_cols] = out[numeric_cols].replace([np.inf, -np.inf], np.nan).round(4)
    out["trade_date"] = out["trade_date"].dt.date.astype(str)
    return out


def generate_historical_scores(features_df: pd.DataFrame) -> pd.DataFrame:
    if features_df is None or features_df.empty:
        return pd.DataFrame()

    df = features_df.copy()
    avg_volume = pd.to_numeric(df.get("volume"), errors="coerce").median()
    avg_trades = pd.to_numeric(df.get("trades"), errors="coerce").median()
    rows = []
    for _, row in df.iterrows():
        metrics = {
            "variation_pct": row.get("return_1d"),
            "last_vs_open_pct": row.get("last_vs_open_pct"),
            "last_vs_prev_close_pct": row.get("return_1d"),
            "position_range_pct": row.get("position_range_pct"),
            "range_pct": row.get("range_pct"),
            "gap_pct": row.get("gap_pct"),
        }
        liquidity = liquidity_profile(
            volume=row.get("volume"),
            trades=row.get("trades"),
            avg_volume=row.get("volume_ma_20", avg_volume),
            avg_trades=row.get("trades_ma_20", avg_trades),
        )
        trend = {
            "price_above_fast_ma": row.get("close") > row.get("moving_average_9"),
            "price_above_slow_ma": row.get("close") > row.get("moving_average_21"),
            "fast_ma_above_slow_ma": row.get("moving_average_9") >= row.get("moving_average_21"),
        }
        scored = score_asset(metrics=metrics, liquidity=liquidity, trend=trend)
        signal = classify_asset_signal(scored)

        item = row.to_dict()
        item.update(
            {
                "score_final": scored["score_final"],
                "score_momentum": scored["score_momentum"],
                "score_tendencia": scored["score_tendencia"],
                "score_liquidez": scored["score_liquidez"],
                "score_volatilidade": scored["score_volatilidade"],
                "score_risco": scored["score_risco"],
                "signal_type": signal["signal_type"],
                "signal_confidence": signal["confidence"],
                "explanation": explain_signal(
                    ticker=str(row.get("ticker")),
                    signal_type=signal["signal_type"],
                    metrics=metrics,
                    liquidity=liquidity,
                    risks=scored["risk_reasons"],
                ),
            }
        )
        rows.append(item)

    return pd.DataFrame(rows)
