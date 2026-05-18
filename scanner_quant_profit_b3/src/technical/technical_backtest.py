"""Backtest exploratorio de setups tecnicos."""
from __future__ import annotations

import pandas as pd


def run_technical_setup_backtest(features_df: pd.DataFrame, setup_type: str | None = None, horizons: list[int] | None = None) -> pd.DataFrame:
    horizons = horizons or [1, 3, 5, 10]
    if features_df.empty or "setup_type" not in features_df.columns:
        return pd.DataFrame()
    work = features_df.copy()
    if work.empty:
        return pd.DataFrame()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce")
    out_frames = []
    max_h = max(horizons)
    for _, group in work.sort_values("trade_date").groupby("ticker", dropna=False):
        g = group.copy().reset_index(drop=True)
        close = pd.to_numeric(g["close"], errors="coerce")
        high = pd.to_numeric(g.get("high", close), errors="coerce")
        low = pd.to_numeric(g.get("low", close), errors="coerce")
        for horizon in horizons:
            g[f"future_return_{horizon}d"] = close.shift(-horizon) / close - 1
            g[f"future_return_{horizon}d"] *= 100
            g[f"hit_{horizon}d"] = (g[f"future_return_{horizon}d"] > 0).astype("Int64")
        mfe = []
        mae = []
        for i in range(len(g)):
            future_high = high.iloc[i + 1 : i + max_h + 1]
            future_low = low.iloc[i + 1 : i + max_h + 1]
            base = close.iloc[i]
            mfe.append(((future_high.max() / base) - 1) * 100 if pd.notna(base) and base else pd.NA)
            mae.append(((future_low.min() / base) - 1) * 100 if pd.notna(base) and base else pd.NA)
        g["max_favorable_excursion"] = mfe
        g["max_adverse_excursion"] = mae
        out_frames.append(g)
    out = pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()
    if out.empty:
        return out
    has_setup = out["setup_type"].notna() & (out["setup_type"].astype(str) != "")
    if setup_type:
        has_setup &= out["setup_type"].astype(str) == setup_type
    return out[has_setup].reset_index(drop=True)


def summarize_technical_backtest(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "setup_type",
        "technical_status",
        "trend_regime",
        "volatility_regime",
        "liquidity_regime",
        "event_context_type",
        "signals",
        "mean_return_5d",
        "median_return_5d",
        "hit_rate_5d",
        "payoff",
        "mean_adverse_excursion",
        "sample_ok",
    ]
    if results_df.empty:
        return pd.DataFrame(columns=columns)
    group_cols = [c for c in ["setup_type", "technical_status", "trend_regime", "volatility_regime", "liquidity_regime", "event_context_type"] if c in results_df.columns]
    if not group_cols:
        group_cols = ["setup_type"]
    rows = []
    for keys, group in results_df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: pd.NA for col in columns}
        for col, value in zip(group_cols, keys):
            row[col] = value
        ret = pd.to_numeric(group.get("future_return_5d"), errors="coerce")
        gains = ret[ret > 0]
        losses = ret[ret < 0].abs()
        row.update(
            {
                "signals": int(len(group)),
                "mean_return_5d": round(float(ret.mean()), 4) if ret.notna().any() else 0.0,
                "median_return_5d": round(float(ret.median()), 4) if ret.notna().any() else 0.0,
                "hit_rate_5d": round(float((ret.dropna() > 0).mean()) * 100, 2) if ret.notna().any() else 0.0,
                "payoff": round(float(gains.mean() / losses.mean()), 4) if not gains.empty and not losses.empty and losses.mean() else 0.0,
                "mean_adverse_excursion": round(float(pd.to_numeric(group.get("max_adverse_excursion"), errors="coerce").mean()), 4)
                if "max_adverse_excursion" in group.columns
                else 0.0,
                "sample_ok": int(len(group) >= 30),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)
