"""Diagnostico fino de custos por evento de saida."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.order_reason_normalizer import normalize_orders_reasons


def _extract_trade_pnl(value) -> float:
    try:
        meta = json.loads(value or "{}") if not isinstance(value, dict) else value
        return float(meta.get("metadata_trade_pnl") or meta.get("net_pnl") or 0)
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0.0


def _classify(row: pd.Series) -> str:
    exits = int(row.get("exit_count") or 0)
    if exits <= 0:
        return "EXIT_RULE_INSUFFICIENT_DATA"
    ratio = row.get("cost_to_pnl_ratio")
    net = float(row.get("net_pnl") or 0)
    if pd.isna(ratio):
        return "EXIT_RULE_INSUFFICIENT_DATA"
    if ratio >= 1.0 or net < 0:
        return "EXIT_RULE_DESTROYS_EDGE"
    if ratio >= 0.35:
        return "EXIT_RULE_COSTLY"
    return "EXIT_RULE_EFFICIENT"


def analyze_exit_rule_costs(orders_df: pd.DataFrame, exit_events_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Agrupar custo atribuido a stop, take-profit, trailing, tempo e fechamento."""
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(
            columns=[
                "exit_rule",
                "exit_count",
                "gross_pnl",
                "net_pnl",
                "transaction_cost",
                "slippage_cost",
                "cost_drag",
                "avg_cost_per_exit",
                "avg_pnl_per_exit",
                "cost_to_pnl_ratio",
                "win_rate_after_cost",
                "exit_rule_cost_class",
                "metadata_json",
            ]
        )
    orders = normalize_orders_reasons(orders_df)
    mask = orders["normalized_order_reason"].astype(str).str.startswith("EXIT_") | orders["normalized_order_reason"].astype(str).eq("CLOSE_POSITION")
    exits = orders[mask].copy()
    if exits.empty:
        return analyze_exit_rule_costs(pd.DataFrame(), exit_events_df)
    exits["transaction_cost"] = pd.to_numeric(exits.get("execution_cost"), errors="coerce").fillna(0)
    exits["slippage_cost"] = pd.to_numeric(exits.get("slippage_cost"), errors="coerce").fillna(0)
    exits["cost_drag"] = exits["transaction_cost"] + exits["slippage_cost"]
    exits["net_pnl"] = exits.get("metadata_trade_pnl", pd.Series(0, index=exits.index)).fillna(0)
    if exits["net_pnl"].astype(str).eq("0").all() or pd.to_numeric(exits["net_pnl"], errors="coerce").fillna(0).abs().sum() == 0:
        exits["net_pnl"] = exits["metadata_json"].apply(_extract_trade_pnl)
    exits["net_pnl"] = pd.to_numeric(exits["net_pnl"], errors="coerce").fillna(0)
    exits["gross_pnl"] = exits["net_pnl"] + exits["cost_drag"]
    grouped = (
        exits.groupby("normalized_order_reason")
        .agg(
            exit_count=("ticker", "count"),
            gross_pnl=("gross_pnl", "sum"),
            net_pnl=("net_pnl", "sum"),
            transaction_cost=("transaction_cost", "sum"),
            slippage_cost=("slippage_cost", "sum"),
            cost_drag=("cost_drag", "sum"),
            win_rate_after_cost=("net_pnl", lambda s: float((s > 0).mean()) if len(s) else 0.0),
        )
        .reset_index()
        .rename(columns={"normalized_order_reason": "exit_rule"})
    )
    grouped["avg_cost_per_exit"] = grouped["cost_drag"] / grouped["exit_count"].replace(0, pd.NA)
    grouped["avg_pnl_per_exit"] = grouped["net_pnl"] / grouped["exit_count"].replace(0, pd.NA)
    grouped["cost_to_pnl_ratio"] = grouped.apply(lambda r: r["cost_drag"] / abs(r["gross_pnl"]) if r["gross_pnl"] else pd.NA, axis=1)
    grouped["exit_rule_cost_class"] = grouped.apply(_classify, axis=1)
    grouped["metadata_json"] = json.dumps({"diagnostic": "evento de saida; nao recomendacao"}, ensure_ascii=False)
    return grouped.sort_values("cost_drag", ascending=False).reset_index(drop=True)


def generate_exit_rule_cost_report(exit_rule_df: pd.DataFrame) -> str:
    if exit_rule_df is None or exit_rule_df.empty:
        return "Sem eventos de saída suficientes para diagnosticar custo atribuído."
    rows = ["Diagnóstico de custos por evento de saída:"]
    for _, row in exit_rule_df.iterrows():
        rows.append(
            f"- {row.get('exit_rule')}: {int(row.get('exit_count') or 0)} eventos, "
            f"cost drag {float(row.get('cost_drag') or 0):.2f}, classe {row.get('exit_rule_cost_class')}."
        )
    rows.append("Resultado analítico: simulação e não recomendação.")
    return "\n".join(rows)
