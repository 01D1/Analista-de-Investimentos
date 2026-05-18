"""Análise de estabilidade técnica por regime e eventos."""
from __future__ import annotations

import pandas as pd


def _ret(df: pd.DataFrame, col: str = "future_return_5d") -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def _payoff(ret: pd.Series) -> float:
    gains = ret[ret > 0]
    losses = ret[ret < 0].abs()
    return round(float(gains.mean() / losses.mean()), 4) if not gains.empty and not losses.empty and losses.mean() else 0.0


def attach_regime_to_technical_results(backtest_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    if backtest_df.empty or regimes_df.empty:
        return backtest_df.copy()
    left = backtest_df.copy()
    right = regimes_df.copy()
    left["trade_date"] = pd.to_datetime(left["trade_date"], errors="coerce").dt.date.astype(str)
    right["trade_date"] = pd.to_datetime(right["trade_date"], errors="coerce").dt.date.astype(str)
    cols = [c for c in ["trade_date", "primary_regime", "trend_regime", "volatility_regime", "liquidity_regime", "risk_regime"] if c in right.columns]
    return left.merge(right[cols].drop_duplicates("trade_date"), on="trade_date", how="left")


def attach_event_context_to_technical_results(backtest_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    out = backtest_df.copy()
    if out.empty:
        return out
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.date.astype(str)
    out["has_event"] = 0
    out["event_type"] = pd.NA
    out["event_context_type"] = "TECNICO_SEM_EVENTO"
    if events_df.empty:
        return out
    events = events_df.copy()
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce").dt.date.astype(str)
    events["ticker"] = events.get("ticker", pd.Series(dtype=str)).astype(str).str.upper()
    out["ticker"] = out["ticker"].astype(str).str.upper()
    cols = [c for c in ["event_date", "ticker", "event_type", "impact_score"] if c in events.columns]
    merged = out.merge(events[cols].rename(columns={"event_date": "trade_date"}), on=["trade_date", "ticker"], how="left", suffixes=("", "_event"))
    event_col = "event_type_event" if "event_type_event" in merged.columns else "event_type"
    has_event = merged[event_col].notna()
    if event_col != "event_type":
        merged["event_type"] = merged[event_col].combine_first(merged.get("event_type"))
    merged["has_event"] = has_event.astype(int)
    merged["event_context_type"] = has_event.map({True: "TECNICO_COM_EVENTO", False: "TECNICO_SEM_EVENTO"})
    return merged


def summarize_technical_by_regime(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["regime_type", "regime_value", "signals_count", "mean_return_5d", "hit_rate_5d", "payoff", "dominant_setup_type", "concentration"]
    if results_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for regime_col in [c for c in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"] if c in results_df.columns]:
        for value, group in results_df.groupby(regime_col, dropna=False):
            ret = _ret(group)
            rows.append(
                {
                    "regime_type": regime_col,
                    "regime_value": value,
                    "signals_count": int(len(group)),
                    "mean_return_5d": round(float(ret.mean()), 4) if ret.notna().any() else 0.0,
                    "hit_rate_5d": round(float((ret.dropna() > 0).mean()) * 100, 2) if ret.notna().any() else 0.0,
                    "payoff": _payoff(ret),
                    "dominant_setup_type": group["setup_type"].mode().iloc[0] if "setup_type" in group.columns and not group["setup_type"].mode().empty else pd.NA,
                    "concentration": round(float(group["ticker"].value_counts(normalize=True).iloc[0] * 100), 2) if "ticker" in group.columns and len(group) else 0.0,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def summarize_technical_by_event_context(results_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["context_type", "context_value", "signals_count", "mean_return_5d", "hit_rate_5d", "payoff", "dominant_setup_type", "concentration"]
    if results_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for col in [c for c in ["has_event", "event_type", "event_context_type"] if c in results_df.columns]:
        for value, group in results_df.groupby(col, dropna=False):
            ret = _ret(group)
            rows.append(
                {
                    "context_type": col,
                    "context_value": value,
                    "signals_count": int(len(group)),
                    "mean_return_5d": round(float(ret.mean()), 4) if ret.notna().any() else 0.0,
                    "hit_rate_5d": round(float((ret.dropna() > 0).mean()) * 100, 2) if ret.notna().any() else 0.0,
                    "payoff": _payoff(ret),
                    "dominant_setup_type": group["setup_type"].mode().iloc[0] if "setup_type" in group.columns and not group["setup_type"].mode().empty else pd.NA,
                    "concentration": round(float(group["ticker"].value_counts(normalize=True).iloc[0] * 100), 2) if "ticker" in group.columns and len(group) else 0.0,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def generate_technical_context_report(regime_summary: pd.DataFrame, event_summary: pd.DataFrame) -> str:
    parts = []
    if regime_summary.empty:
        parts.append("Não há dados suficientes para estabilidade por regime.")
    else:
        best = regime_summary.sort_values("mean_return_5d", ascending=False).iloc[0]
        parts.append(f"Melhor leitura por regime: {best['regime_type']}={best['regime_value']} com retorno médio D+5 de {best['mean_return_5d']}%.")
    if event_summary.empty:
        parts.append("Não há cobertura suficiente para evento x sem evento.")
    else:
        best = event_summary.sort_values("mean_return_5d", ascending=False).iloc[0]
        parts.append(f"Melhor contexto de eventos: {best['context_type']}={best['context_value']} com retorno médio D+5 de {best['mean_return_5d']}%.")
    return " ".join(parts)
