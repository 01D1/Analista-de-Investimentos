"""Diagnostico fino de custo de rebalanceamento simulado."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.order_reason_normalizer import normalize_orders_reasons


def _cost_class(cost_pct: float | None, orders_count: int) -> str:
    if orders_count <= 0:
        return "REBALANCE_DATA_INSUFFICIENT"
    if cost_pct is None:
        return "REBALANCE_DATA_INSUFFICIENT"
    if cost_pct >= 0.5:
        return "REBALANCE_COST_DOMINATES_EDGE"
    if cost_pct >= 0.2:
        return "REBALANCE_COST_HIGH"
    return "REBALANCE_COST_OK"


def _cost_frame(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "rebalance_orders_count", "rebalance_cost_total", "rebalance_slippage_total"])
    work = df.copy()
    work["cost_drag"] = pd.to_numeric(work.get("execution_cost"), errors="coerce").fillna(0) + pd.to_numeric(work.get("slippage_cost"), errors="coerce").fillna(0)
    return (
        work.groupby(group_col)
        .agg(
            rebalance_orders_count=("ticker", "count"),
            rebalance_cost_total=("cost_drag", "sum"),
            rebalance_slippage_total=("slippage_cost", "sum"),
        )
        .reset_index()
        .sort_values("rebalance_cost_total", ascending=False)
    )


def analyze_rebalance_costs(orders_df: pd.DataFrame, rebalance_events_df: pd.DataFrame | None = None) -> dict:
    """Diagnosticar custo atribuido a rebalanceamento simulado."""
    if orders_df is None or orders_df.empty:
        return {
            "summary": {"rebalance_orders_count": 0, "rebalance_cost_class": "REBALANCE_DATA_INSUFFICIENT"},
            "rebalance_cost_by_ticker": pd.DataFrame(),
            "rebalance_cost_by_date": pd.DataFrame(),
            "rebalance_cost_by_reason": pd.DataFrame(),
        }
    orders = normalize_orders_reasons(orders_df)
    total_cost = pd.to_numeric(orders.get("execution_cost"), errors="coerce").fillna(0).sum() + pd.to_numeric(orders.get("slippage_cost"), errors="coerce").fillna(0).sum()
    mask = orders["normalized_order_reason"].astype(str).str.startswith("REBALANCE") | orders.get("signal_source", pd.Series("", index=orders.index)).astype(str).str.upper().eq("REBALANCE")
    reb = orders[mask].copy()
    reb["cost_drag"] = pd.to_numeric(reb.get("execution_cost"), errors="coerce").fillna(0) + pd.to_numeric(reb.get("slippage_cost"), errors="coerce").fillna(0)
    cost_total = float(reb["cost_drag"].sum()) if not reb.empty else 0.0
    slippage_total = float(pd.to_numeric(reb.get("slippage_cost"), errors="coerce").fillna(0).sum()) if not reb.empty else 0.0
    pct = cost_total / total_cost if total_cost else None
    summary = {
        "rebalance_orders_count": int(len(reb)),
        "rebalance_cost_total": cost_total,
        "rebalance_slippage_total": slippage_total,
        "avg_rebalance_cost": cost_total / len(reb) if len(reb) else 0.0,
        "rebalance_cost_to_total_cost_pct": pct,
        "rebalance_pnl_after_event": None,
        "rebalance_cost_class": _cost_class(pct, len(reb)),
        "metadata_json": json.dumps({"diagnostic": "rebalanceamento simulado; nao recomendacao"}, ensure_ascii=False),
    }
    return {
        "summary": summary,
        "rebalance_cost_by_ticker": _cost_frame(reb, "ticker"),
        "rebalance_cost_by_date": _cost_frame(reb, "trade_date"),
        "rebalance_cost_by_reason": _cost_frame(reb, "normalized_order_reason").rename(columns={"normalized_order_reason": "rebalance_reason"}),
    }


def suggest_rebalance_diagnostics(rebalance_summary: dict) -> list[str]:
    """Sugerir novas simulacoes diagnosticas sem aplicacao automatica."""
    klass = str(rebalance_summary.get("rebalance_cost_class", "REBALANCE_DATA_INSUFFICIENT"))
    suggestions = [
        "Simular reducao de frequencia de rebalanceamento sem aplicar automaticamente.",
        "Testar threshold minimo de diferenca de peso antes de gerar ordem.",
        "Agrupar rebalanceamentos para reduzir turnover simulado.",
        "Bloquear rebalanceamento apenas em estudo quando liquidez estiver fraca.",
        "Comparar rebalance semanal vs mensal em nova simulacao.",
    ]
    if klass == "REBALANCE_DATA_INSUFFICIENT":
        return ["Coletar ou enriquecer metadata de rebalance_event_id antes de concluir."] + suggestions[-1:]
    return suggestions
