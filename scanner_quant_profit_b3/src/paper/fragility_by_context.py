"""Fragilidade por regime e contexto de evento."""
from __future__ import annotations

import pandas as pd


def _num(group: pd.DataFrame, col: str, default=0) -> pd.Series:
    if col in group.columns:
        return pd.to_numeric(group[col], errors="coerce").fillna(default)
    return pd.Series([default] * len(group), index=group.index)


def _merge_by_date(results_df: pd.DataFrame, context_df: pd.DataFrame, date_col: str = "trade_date") -> pd.DataFrame:
    out = results_df.copy()
    if "trade_date" not in out.columns:
        out["trade_date"] = out.get("start_date", "")
    out["trade_date"] = out["trade_date"].astype(str)
    if context_df is None or context_df.empty or date_col not in context_df.columns:
        return out
    ctx = context_df.copy()
    ctx[date_col] = ctx[date_col].astype(str)
    return out.merge(ctx.drop_duplicates(date_col), left_on="trade_date", right_on=date_col, how="left")


def analyze_paper_by_regime(results_df: pd.DataFrame, regimes_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["regime_type", "regime_value", "trades", "net_pnl", "win_rate", "avg_return", "max_drawdown", "cost_drag", "slippage_drag", "metadata_json"]
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=columns)
    work = _merge_by_date(results_df, regimes_df, "trade_date")
    rows = []
    for col in ["primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"]:
        if col not in work.columns:
            work[col] = "INDEFINIDO"
        for value, group in work.groupby(col, dropna=False):
            ret = pd.to_numeric(group.get("net_pnl", group.get("total_return", 0)), errors="coerce").fillna(0)
            rows.append(
                {
                    "regime_type": col,
                    "regime_value": value if pd.notna(value) else "INDEFINIDO",
                    "trades": int(pd.to_numeric(group.get("trades_count", group.get("trades", 0)), errors="coerce").fillna(0).sum()),
                    "net_pnl": round(float(ret.sum()), 6),
                    "win_rate": round(float(pd.to_numeric(group.get("win_rate"), errors="coerce").fillna(0).mean()), 6),
                    "avg_return": round(float(ret.mean()), 6),
                    "max_drawdown": round(float(pd.to_numeric(group.get("max_drawdown", 0), errors="coerce").fillna(0).min()), 6),
                    "cost_drag": round(float(_num(group, "cost_drag").sum()), 6),
                    "slippage_drag": round(float(_num(group, "slippage_cost").sum()), 6),
                    "metadata_json": "{}",
                }
            )
    return pd.DataFrame(rows, columns=columns)


def analyze_paper_by_event_context(results_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["event_group", "event_value", "trades", "net_pnl", "win_rate", "avg_return", "cost_drag", "metadata_json"]
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=columns)
    work = _merge_by_date(results_df, events_df, "event_date" if events_df is not None and "event_date" in events_df.columns else "trade_date")
    rows = []
    for col in ["has_event", "event_type", "event_context_type"]:
        if col not in work.columns:
            work[col] = "INDEFINIDO"
        for value, group in work.groupby(col, dropna=False):
            ret = pd.to_numeric(group.get("net_pnl", group.get("total_return", 0)), errors="coerce").fillna(0)
            rows.append({"event_group": col, "event_value": value, "trades": int(len(group)), "net_pnl": round(float(ret.sum()), 6), "win_rate": round(float(pd.to_numeric(group.get("win_rate"), errors="coerce").fillna(0).mean()), 6), "avg_return": round(float(ret.mean()), 6), "cost_drag": round(float(_num(group, "cost_drag").sum()), 6), "metadata_json": "{}"})
    return pd.DataFrame(rows, columns=columns)


def generate_context_fragility_report(regime_df: pd.DataFrame, event_df: pd.DataFrame) -> str:
    parts = []
    if regime_df is not None and not regime_df.empty:
        worst = regime_df.sort_values("net_pnl").iloc[0]
        parts.append(f"Regime com maior contribuicao negativa: {worst['regime_type']}={worst['regime_value']}.")
    if event_df is not None and not event_df.empty:
        worst = event_df.sort_values("net_pnl").iloc[0]
        parts.append(f"Contexto de evento com maior contribuicao negativa: {worst['event_group']}={worst['event_value']}.")
    return " ".join(parts) if parts else "Contexto insuficiente para diagnostico de fragilidade."
