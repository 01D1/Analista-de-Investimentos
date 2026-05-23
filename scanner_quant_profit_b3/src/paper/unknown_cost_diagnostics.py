"""Diagnostico de custos atribuidos a UNKNOWN e metadata ausente."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.order_reason_normalizer import normalize_orders_reasons


def _missing_counter(df: pd.DataFrame) -> dict:
    counter: dict[str, int] = {}
    for value in df.get("missing_metadata_fields", []):
        fields = value if isinstance(value, list) else []
        for field in fields:
            counter[field] = counter.get(field, 0) + 1
    return dict(sorted(counter.items(), key=lambda item: item[1], reverse=True))


def _group_unknown(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return pd.DataFrame(columns=[col, "unknown_orders_count", "unknown_cost_total", "unknown_slippage_total"])
    work = df.copy()
    work["cost_drag"] = pd.to_numeric(work.get("execution_cost"), errors="coerce").fillna(0) + pd.to_numeric(work.get("slippage_cost"), errors="coerce").fillna(0)
    return (
        work.groupby(col)
        .agg(
            unknown_orders_count=("ticker", "count"),
            unknown_cost_total=("cost_drag", "sum"),
            unknown_slippage_total=("slippage_cost", "sum"),
        )
        .reset_index()
        .sort_values("unknown_cost_total", ascending=False)
    )


def suggest_metadata_fixes(unknown_summary: dict) -> list[str]:
    """Sugerir correcoes futuras de metadata sem alterar historico."""
    missing = unknown_summary.get("missing_fields_summary") or {}
    fixes = []
    if "signal_source" in missing:
        fixes.append("Garantir signal_source em toda ordem simulada.")
    if "exit_rule_triggered" in missing:
        fixes.append("Preencher exit_rule_triggered e exit_reason em todo evento de saída.")
    if "metadata_json" in missing:
        fixes.append("Persistir metadata_json mesmo quando o payload estiver vazio.")
    if "rebalance_event_id" in missing:
        fixes.append("Marcar rebalance_event_id nas ordens de rebalanceamento simulado.")
    if "lifecycle_id" in missing:
        fixes.append("Gravar lifecycle_id para vincular entrada, saída e rebalanceamento.")
    if "parent_signal_id" in missing:
        fixes.append("Gravar parent_signal_id nas ordens originadas por sinal.")
    fixes.extend(
        [
            "Marcar is_simulation_end_close no fechamento de simulação.",
            "Gravar cost_bucket para entrada, saída, rebalanceamento e fechamento de simulação.",
        ]
    )
    return list(dict.fromkeys(fixes))


def analyze_unknown_costs(orders_df: pd.DataFrame) -> dict:
    """Identificar custo atribuido a UNKNOWN e campos de metadata ausentes."""
    if orders_df is None or orders_df.empty:
        summary = {
            "unknown_orders_count": 0,
            "unknown_cost_total": 0.0,
            "unknown_slippage_total": 0.0,
            "missing_fields_summary": {},
            "missing_fields_summary_json": "{}",
            "required_metadata_fixes": [],
            "required_metadata_fixes_json": "[]",
            "metadata_json": "{}",
        }
        return {"summary": summary, "unknown_by_ticker": pd.DataFrame(), "unknown_by_date": pd.DataFrame(), "unknown_by_side": pd.DataFrame()}
    orders = normalize_orders_reasons(orders_df)
    missing_any = orders.get("missing_metadata_fields", pd.Series([], dtype=object)).apply(lambda fields: bool(fields) if isinstance(fields, list) else False)
    unknown = orders[(orders["is_unknown"].astype(bool)) | missing_any].copy()
    unknown["cost_drag"] = pd.to_numeric(unknown.get("execution_cost"), errors="coerce").fillna(0) + pd.to_numeric(unknown.get("slippage_cost"), errors="coerce").fillna(0)
    missing = _missing_counter(unknown)
    summary = {
        "unknown_orders_count": int(len(unknown)),
        "unknown_cost_total": float(unknown["cost_drag"].sum()) if not unknown.empty else 0.0,
        "unknown_slippage_total": float(pd.to_numeric(unknown.get("slippage_cost"), errors="coerce").fillna(0).sum()) if not unknown.empty else 0.0,
        "missing_fields_summary": missing,
        "missing_fields_summary_json": json.dumps(missing, ensure_ascii=False),
        "metadata_json": json.dumps({"diagnostic": "metadado ausente; nao recomendacao"}, ensure_ascii=False),
    }
    fixes = suggest_metadata_fixes(summary)
    summary["required_metadata_fixes"] = fixes
    summary["required_metadata_fixes_json"] = json.dumps(fixes, ensure_ascii=False)
    return {
        "summary": summary,
        "unknown_by_ticker": _group_unknown(unknown, "ticker"),
        "unknown_by_date": _group_unknown(unknown, "trade_date"),
        "unknown_by_side": _group_unknown(unknown, "side"),
    }
