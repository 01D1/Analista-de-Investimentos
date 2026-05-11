"""Classificação de regimes de mercado para pesquisa quantitativa."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REGIME_COLUMNS = [
    "trade_date",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
    "regime_confidence",
]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return default if pd.isna(out) else out
    except (TypeError, ValueError):
        return default


def build_market_proxy_from_universe(daily_prices_df: pd.DataFrame) -> pd.DataFrame:
    """Cria proxy de mercado pela média dos ativos quando não há benchmark oficial."""
    if daily_prices_df is None or daily_prices_df.empty:
        return pd.DataFrame(
            columns=[
                "trade_date",
                "market_return_mean",
                "market_return_median",
                "pct_assets_positive",
                "total_volume",
                "universe_volatility",
                "market_breadth",
            ]
        )
    df = daily_prices_df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df.get("volume"), errors="coerce")
    df = df.dropna(subset=["trade_date", "ticker", "close"]).sort_values(["ticker", "trade_date"])
    df["asset_return_1d"] = df.groupby("ticker")["close"].pct_change() * 100.0
    rows = []
    for date, group in df.groupby("trade_date"):
        returns = pd.to_numeric(group["asset_return_1d"], errors="coerce").dropna()
        rows.append(
            {
                "trade_date": date.date().isoformat(),
                "market_return_mean": round(float(returns.mean()), 4) if not returns.empty else 0.0,
                "market_return_median": round(float(returns.median()), 4) if not returns.empty else 0.0,
                "pct_assets_positive": round(float((returns > 0).mean() * 100.0), 4) if not returns.empty else 0.0,
                "total_volume": round(float(pd.to_numeric(group.get("volume"), errors="coerce").sum()), 4),
                "universe_volatility": round(float(returns.std(ddof=0)), 4) if len(returns) > 1 else 0.0,
                "market_breadth": round(float((returns > 0).mean() * 100.0), 4) if not returns.empty else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _ensure_close(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "close" not in out.columns or pd.to_numeric(out.get("close"), errors="coerce").isna().all():
        returns = pd.to_numeric(out.get("market_return_mean"), errors="coerce").fillna(0.0) / 100.0
        out["close"] = 100.0 * (1.0 + returns).cumprod()
    return out


def classify_market_regime(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    item = pd.Series(row) if not isinstance(row, pd.Series) else row
    ret20 = _num(item.get("return_20d"))
    trend_strength = _num(item.get("trend_strength"))
    vol20 = _num(item.get("volatility_20d"))
    vol60 = _num(item.get("volatility_60d"), default=vol20)
    volume_rel = _num(item.get("volume_relative_20d"), default=1.0)
    drawdown20 = _num(item.get("drawdown_20d"))

    if ret20 > 2.0 and trend_strength > 1.0:
        trend = "ALTA_TENDENCIAL"
    elif ret20 < -2.0 and trend_strength < -1.0:
        trend = "BAIXA_TENDENCIAL"
    elif abs(ret20) <= 1.0 and abs(trend_strength) <= 1.0:
        trend = "LATERAL"
    else:
        trend = "INDEFINIDO"

    if vol60 and vol20 >= vol60 * 1.5:
        volatility = "ALTA_VOLATILIDADE"
    elif vol60 and vol20 <= vol60 * 0.7:
        volatility = "BAIXA_VOLATILIDADE"
    else:
        volatility = "BAIXA_VOLATILIDADE" if vol20 <= 1.5 else "ALTA_VOLATILIDADE"

    if volume_rel >= 1.2:
        liquidity = "LIQUIDEZ_FORTE"
    elif volume_rel <= 0.7:
        liquidity = "LIQUIDEZ_FRACA"
    else:
        liquidity = "LIQUIDEZ_FORTE" if volume_rel >= 1.0 else "LIQUIDEZ_FRACA"

    risk = "RISCO_ELEVADO" if drawdown20 <= -5.0 or volatility == "ALTA_VOLATILIDADE" else "RISCO_CONTROLADO"
    primary = risk if risk == "RISCO_ELEVADO" and trend == "BAIXA_TENDENCIAL" else trend
    if primary == "INDEFINIDO":
        primary = volatility if volatility == "ALTA_VOLATILIDADE" else "INDEFINIDO"
    confidence = 0.75 if primary != "INDEFINIDO" else 0.35
    return {
        "primary_regime": primary,
        "trend_regime": trend,
        "volatility_regime": volatility,
        "liquidity_regime": liquidity,
        "risk_regime": risk,
        "regime_confidence": confidence,
    }


def calculate_market_regime_features(market_df: pd.DataFrame) -> pd.DataFrame:
    if market_df is None or market_df.empty:
        return pd.DataFrame(columns=REGIME_COLUMNS)
    df = _ensure_close(market_df)
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df = df.dropna(subset=["trade_date"]).sort_values("trade_date").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "total_volume"]:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    volume_col = "total_volume" if "total_volume" in df.columns and df["total_volume"].notna().any() else "volume"
    df["return_1d"] = df["close"].pct_change() * 100.0
    df["return_5d"] = df["close"].pct_change(5) * 100.0
    df["return_20d"] = df["close"].pct_change(20) * 100.0
    df["volatility_20d"] = df["return_1d"].rolling(20, min_periods=2).std(ddof=0)
    df["volatility_60d"] = df["return_1d"].rolling(60, min_periods=2).std(ddof=0)
    df["volume_relative_20d"] = df[volume_col] / df[volume_col].rolling(20, min_periods=1).mean().replace(0, np.nan)
    df["moving_average_20"] = df["close"].rolling(20, min_periods=1).mean()
    df["moving_average_50"] = df["close"].rolling(50, min_periods=1).mean()
    df["moving_average_200"] = df["close"].rolling(200, min_periods=1).mean()
    df["distance_from_ma20"] = (df["close"] / df["moving_average_20"].replace(0, np.nan) - 1.0) * 100.0
    df["distance_from_ma50"] = (df["close"] / df["moving_average_50"].replace(0, np.nan) - 1.0) * 100.0
    df["trend_strength"] = df["distance_from_ma20"] + (df["moving_average_20"] / df["moving_average_50"].replace(0, np.nan) - 1.0) * 100.0
    df["drawdown_20d"] = (df["close"] / df["close"].rolling(20, min_periods=1).max().replace(0, np.nan) - 1.0) * 100.0
    df["drawdown_60d"] = (df["close"] / df["close"].rolling(60, min_periods=1).max().replace(0, np.nan) - 1.0) * 100.0
    regimes = df.apply(classify_market_regime, axis=1, result_type="expand")
    out = pd.concat([df, regimes], axis=1)
    out["trade_date"] = out["trade_date"].dt.date.astype(str)
    numeric_cols = out.select_dtypes(include=["number"]).columns
    out[numeric_cols] = out[numeric_cols].replace([np.inf, -np.inf], np.nan).round(4)
    return out


def assign_regimes_to_backtest(backtest_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame()
    out = backtest_df.copy()
    if regimes_df is None or regimes_df.empty:
        for col in REGIME_COLUMNS[1:]:
            out[col] = pd.NA
        return out
    regimes = regimes_df[REGIME_COLUMNS].copy()
    regimes["trade_date"] = pd.to_datetime(regimes["trade_date"], errors="coerce").dt.date.astype(str)
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.date.astype(str)
    return out.merge(regimes, on="trade_date", how="left")
