"""Validacao da carteira simulada por regime de mercado."""
from __future__ import annotations

import pandas as pd


def attach_regime_to_paper_results(results_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame()
    out = results_df.copy()
    if regimes_df is None or regimes_df.empty or "trade_date" not in regimes_df.columns:
        for col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"]:
            out[col] = "INDEFINIDO"
        return out
    regimes = regimes_df.copy()
    regimes["trade_date"] = regimes["trade_date"].astype(str)
    cols = ["trade_date"] + [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"] if c in regimes.columns]
    regimes = regimes[cols].drop_duplicates("trade_date").rename(columns={"trade_date": "start_date"})
    out["start_date"] = out["start_date"].astype(str)
    out = out.merge(regimes, on="start_date", how="left")
    for col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"]:
        if col not in out.columns:
            out[col] = "INDEFINIDO"
        out[col] = out[col].fillna("INDEFINIDO")
    return out


def summarize_paper_by_regime(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["regime_type", "regime_value", "signals_count", "mean_return", "mean_drawdown", "trades", "win_rate", "profit_factor", "turnover", "concentration_pct", "metadata_json"]
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for regime_col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"]:
        if regime_col not in results_df.columns:
            continue
        for value, group in results_df.groupby(regime_col, dropna=False):
            rows.append(
                {
                    "regime_type": regime_col,
                    "regime_value": value,
                    "signals_count": int(len(group)),
                    "mean_return": round(float(pd.to_numeric(group["total_return"], errors="coerce").fillna(0).mean()), 6),
                    "mean_drawdown": round(float(pd.to_numeric(group["max_drawdown"], errors="coerce").fillna(0).mean()), 6),
                    "trades": int(pd.to_numeric(group["trades_count"], errors="coerce").fillna(0).sum()),
                    "win_rate": round(float(pd.to_numeric(group["win_rate"], errors="coerce").fillna(0).mean()), 6),
                    "profit_factor": round(float(pd.to_numeric(group["profit_factor"], errors="coerce").fillna(0).mean()), 6),
                    "turnover": round(float(pd.to_numeric(group["turnover"], errors="coerce").fillna(0).mean()), 2),
                    "concentration_pct": round(float(len(group) / max(len(results_df), 1)), 4),
                    "metadata_json": "{}",
                }
            )
    return pd.DataFrame(rows, columns=columns)
