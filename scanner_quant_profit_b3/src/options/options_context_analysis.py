"""Análise de contexto por regime e eventos para backtests de opções."""
from __future__ import annotations

import pandas as pd

from src.options.options_backtest_summary import summarize_structure_backtest


def attach_regime_context_to_options_results(results_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame()
    out = results_df.copy()
    if regimes_df is None or regimes_df.empty:
        for col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"]:
            out[col] = pd.NA
        return out
    cols = [c for c in ["trade_date", "primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in regimes_df.columns]
    regimes = regimes_df[cols].drop_duplicates("trade_date")
    return out.merge(regimes, left_on="entry_date", right_on="trade_date", how="left").drop(columns=["trade_date"], errors="ignore")


def attach_event_context_to_options_results(results_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame()
    out = results_df.copy()
    if events_df is None or events_df.empty:
        out["has_event"] = False
        out["event_type"] = pd.NA
        out["event_context_type"] = pd.NA
        out["event_impact_score"] = pd.NA
        return out
    events = events_df.copy()
    if "ticker" not in events.columns:
        events["ticker"] = pd.NA
    cols = [c for c in ["event_date", "ticker", "event_type", "event_context_type", "impact_score", "event_impact_score"] if c in events.columns]
    events = events[cols].drop_duplicates(["event_date", "ticker"])
    merged = out.merge(events, left_on=["entry_date", "underlying"], right_on=["event_date", "ticker"], how="left")
    merged["has_event"] = merged["event_date"].notna()
    if "event_context_type" not in merged.columns:
        merged["event_context_type"] = merged["event_type"].where(merged["has_event"], pd.NA)
    if "event_impact_score" not in merged.columns:
        merged["event_impact_score"] = merged.get("impact_score")
    return merged.drop(columns=["event_date", "ticker", "impact_score"], errors="ignore")


def _summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    columns = [group_col, "trades", "mean_net_return", "win_rate", "profit_factor", "avg_cost_drag", "skipped_pct"]
    if df is None or df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for value, group in df.groupby(group_col, dropna=False):
        s = summarize_structure_backtest(group)
        skipped_pct = s["skipped_count"] / s["total_trades"] * 100 if s["total_trades"] else 0
        rows.append(
            {
                group_col: value,
                "trades": s["total_trades"],
                "mean_net_return": s["mean_net_return"],
                "win_rate": s["win_rate"],
                "profit_factor": s["profit_factor"],
                "avg_cost_drag": s["avg_cost_drag"],
                "skipped_pct": round(float(skipped_pct), 4),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_options_by_regime(results_df: pd.DataFrame) -> pd.DataFrame:
    return _summary(results_df, "primary_regime")


def summarize_options_by_event_context(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=["context_type", "context_value", "trades", "mean_net_return", "win_rate", "profit_factor", "avg_cost_drag", "skipped_pct"])
    frames = []
    for col in ["has_event", "event_type", "event_context_type"]:
        if col in results_df.columns:
            part = _summary(results_df, col).rename(columns={col: "context_value"})
            part.insert(0, "context_type", col)
            frames.append(part)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def generate_options_context_report(regime_summary: pd.DataFrame, event_summary: pd.DataFrame) -> str:
    regime_txt = "sem resumo por regime" if regime_summary is None or regime_summary.empty else f"{len(regime_summary)} grupos de regime avaliados"
    event_txt = "sem resumo por evento" if event_summary is None or event_summary.empty else f"{len(event_summary)} grupos de evento avaliados"
    return f"Contexto de opções calculado: {regime_txt}; {event_txt}. Leitura analítica, não recomendação."

