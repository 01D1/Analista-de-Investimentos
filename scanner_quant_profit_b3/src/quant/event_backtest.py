"""Análise estatística de sinais com e sem contexto de eventos."""
from __future__ import annotations

import pandas as pd


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def _top_asset_concentration(group: pd.DataFrame) -> float:
    if group.empty or "ticker" not in group.columns:
        return 0.0
    counts = group["ticker"].value_counts(normalize=True)
    return round(float(counts.iloc[0] * 100), 2) if not counts.empty else 0.0


def _summarize_group(group_type: str, group_value, group: pd.DataFrame) -> dict:
    gross = _num(group, "future_return_5d")
    net = _num(group, "net_return_5d") if "net_return_5d" in group.columns else gross
    return {
        "group_type": group_type,
        "group_value": group_value,
        "signals": int(len(group)),
        "mean_gross_return_5d": round(float(gross.mean()), 4) if gross.notna().any() else 0.0,
        "mean_net_return_5d": round(float(net.mean()), 4) if net.notna().any() else 0.0,
        "hit_rate_5d": round(float((net.dropna() > 0).mean()), 4) if net.notna().any() else 0.0,
        "avg_score_final": round(float(_num(group, "score_final").mean()), 4) if "score_final" in group.columns else 0.0,
        "top_asset_concentration_pct": _top_asset_concentration(group),
        "execution_quality": group["execution_quality"].mode().iloc[0] if "execution_quality" in group.columns and not group["execution_quality"].dropna().empty else None,
    }


def summarize_backtest_by_event_context(backtest_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "group_type",
        "group_value",
        "signals",
        "mean_gross_return_5d",
        "mean_net_return_5d",
        "hit_rate_5d",
        "avg_score_final",
        "top_asset_concentration_pct",
        "execution_quality",
    ]
    if backtest_df is None or backtest_df.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    df = backtest_df.copy()
    for col in ["has_event", "event_context_type", "event_type", "impact_direction"]:
        if col not in df.columns:
            continue
        for value, group in df.groupby(col, dropna=False):
            rows.append(_summarize_group(col, value, group))
    return pd.DataFrame(rows, columns=columns)


def compare_event_vs_no_event(backtest_df: pd.DataFrame) -> dict:
    if backtest_df is None or backtest_df.empty:
        return {
            "signals_with_event": 0,
            "signals_without_event": 0,
            "mean_net_return_with_event": 0.0,
            "mean_net_return_without_event": 0.0,
            "hit_rate_with_event": 0.0,
            "hit_rate_without_event": 0.0,
            "events_positive_helped": False,
            "events_negative_hurt": False,
        }
    df = backtest_df.copy()
    has_event = df.get("has_event", False).astype(bool)
    net = _num(df, "net_return_5d") if "net_return_5d" in df.columns else _num(df, "future_return_5d")
    positive_events = df.get("impact_direction", "").astype(str).str.upper().eq("POSITIVO")
    negative_events = df.get("impact_direction", "").astype(str).str.upper().eq("NEGATIVO")
    return {
        "signals_with_event": int(has_event.sum()),
        "signals_without_event": int((~has_event).sum()),
        "mean_net_return_with_event": round(float(net[has_event].mean()), 4) if net[has_event].notna().any() else 0.0,
        "mean_net_return_without_event": round(float(net[~has_event].mean()), 4) if net[~has_event].notna().any() else 0.0,
        "hit_rate_with_event": round(float((net[has_event].dropna() > 0).mean()), 4) if net[has_event].notna().any() else 0.0,
        "hit_rate_without_event": round(float((net[~has_event].dropna() > 0).mean()), 4) if net[~has_event].notna().any() else 0.0,
        "events_positive_helped": bool(net[positive_events & has_event].mean() > 0) if (positive_events & has_event).any() else False,
        "events_negative_hurt": bool(net[negative_events & has_event].mean() < 0) if (negative_events & has_event).any() else False,
    }


def generate_event_context_report(summary: pd.DataFrame | dict) -> str:
    if isinstance(summary, dict):
        total = int(summary.get("signals_with_event", 0) + summary.get("signals_without_event", 0))
        with_event = summary.get("mean_net_return_with_event", 0.0)
        without_event = summary.get("mean_net_return_without_event", 0.0)
    elif summary is not None and not summary.empty:
        context = summary[summary["group_type"] == "has_event"]
        total = int(context["signals"].sum()) if not context.empty else int(summary["signals"].max())
        with_rows = context[context["group_value"].astype(str).isin(["1", "True", "true"])]
        without_rows = context[context["group_value"].astype(str).isin(["0", "False", "false"])]
        with_event = float(with_rows["mean_net_return_5d"].iloc[0]) if not with_rows.empty else 0.0
        without_event = float(without_rows["mean_net_return_5d"].iloc[0]) if not without_rows.empty else 0.0
    else:
        return "Nenhuma amostra de evento foi encontrada para análise."
    if total < 30:
        caveat = "A amostra de eventos ainda é pequena e não permite conclusão robusta."
    else:
        caveat = "A leitura deve ser validada por regime e fora da amostra."
    return (
        f"Na amostra analisada, sinais com evento tiveram retorno líquido médio de {with_event:.4f}% "
        f"contra {without_event:.4f}% em sinais sem evento. {caveat} "
        "Esta análise separa contexto event-driven de sinais técnicos e não altera o ranking."
    )
