"""Separacao de custos pelo ciclo de vida da posicao."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.paper.order_reason_normalizer import normalize_orders_reasons


def _num(value: Any) -> float:
    try:
        out = pd.to_numeric(value, errors="coerce")
        return 0.0 if pd.isna(out) else float(out)
    except Exception:
        return 0.0


def _cost(row: pd.Series) -> float:
    return _num(row.get("execution_cost")) + _num(row.get("slippage_cost"))


def _metadata(row: pd.Series) -> dict:
    value = row.get("metadata_json")
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _orders_payload(rows: list[pd.Series]) -> str:
    payload = []
    for row in rows:
        payload.append(
            {
                "order_id": row.get("id") or row.get("order_id"),
                "trade_date": row.get("trade_date"),
                "side": row.get("side"),
                "reason": row.get("normalized_order_reason"),
                "cost": _cost(row),
            }
        )
    return json.dumps(payload, ensure_ascii=False, default=str)


def _finalize_lifecycle(lifecycle: dict) -> dict:
    all_rows = lifecycle.pop("_rows", [])
    entry_rows = lifecycle.pop("_entry_rows", [])
    exit_rows = lifecycle.pop("_exit_rows", [])
    rebalance_rows = lifecycle.pop("_rebalance_rows", [])
    gross_pnl = 0.0
    net_pnl = 0.0
    for row in all_rows:
        meta = _metadata(row)
        trade_pnl = _num(meta.get("metadata_trade_pnl") or row.get("metadata_trade_pnl"))
        net_pnl += trade_pnl
        gross_pnl += _num(meta.get("gross_pnl")) or trade_pnl + _cost(row)
    total_cost = sum(_cost(r) for r in all_rows)
    total_slippage = sum(_num(r.get("slippage_cost")) for r in all_rows)
    entry_date = lifecycle.get("entry_date")
    exit_date = lifecycle.get("exit_date")
    holding_days = None
    if entry_date and exit_date:
        try:
            holding_days = int((pd.to_datetime(exit_date) - pd.to_datetime(entry_date)).days)
        except Exception:
            holding_days = None
    lifecycle.update(
        {
            "entry_orders": _orders_payload(entry_rows),
            "exit_orders": _orders_payload(exit_rows),
            "rebalance_orders": _orders_payload(rebalance_rows),
            "holding_days": holding_days,
            "entry_cost": sum(_cost(r) for r in entry_rows),
            "exit_cost": sum(_cost(r) for r in exit_rows),
            "rebalance_cost": sum(_cost(r) for r in rebalance_rows),
            "total_cost": total_cost,
            "total_slippage": total_slippage,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "cost_to_pnl_ratio": total_cost / abs(gross_pnl) if gross_pnl else None,
            "metadata_json": json.dumps({"diagnostic": "custo atribuido por lifecycle simulado"}, ensure_ascii=False),
        }
    )
    return lifecycle


def link_orders_to_position_lifecycle(orders_df: pd.DataFrame, positions_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Vincular ordens a ciclos simples de posicao por ativo.

    A associacao e diagnostica. Historicos sem `lifecycle_id` recebem um id
    sintetico por ticker e sequencia de abertura/fechamento.
    """
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(
            columns=[
                "lifecycle_id",
                "ticker",
                "entry_date",
                "exit_date",
                "entry_orders",
                "exit_orders",
                "rebalance_orders",
                "holding_days",
                "entry_cost",
                "exit_cost",
                "rebalance_cost",
                "total_cost",
                "total_slippage",
                "gross_pnl",
                "net_pnl",
                "cost_to_pnl_ratio",
                "metadata_json",
            ]
        )
    orders = normalize_orders_reasons(orders_df)
    orders["_sort_date"] = pd.to_datetime(orders.get("trade_date"), errors="coerce")
    orders = orders.sort_values(["ticker", "_sort_date", "id"] if "id" in orders.columns else ["ticker", "_sort_date"]).reset_index(drop=True)
    lifecycles = []
    for ticker, group in orders.groupby(orders["ticker"].astype(str)):
        current = None
        seq = 0
        for _, row in group.iterrows():
            reason = str(row.get("normalized_order_reason", "UNKNOWN"))
            side = str(row.get("side", "")).upper()
            is_entry = reason == "ENTRY_SIGNAL" and side in {"BUY", "ENTRY"}
            is_exit = reason.startswith("EXIT_") or reason == "CLOSE_POSITION" or side in {"CLOSE", "SELL"}
            is_rebalance = reason.startswith("REBALANCE") or reason == "REDUCE_POSITION"
            if current is None:
                seq += 1
                current = {
                    "lifecycle_id": row.get("lifecycle_id") or f"{ticker}-{seq:03d}",
                    "ticker": ticker,
                    "entry_date": row.get("trade_date") if is_entry else None,
                    "exit_date": None,
                    "_rows": [],
                    "_entry_rows": [],
                    "_exit_rows": [],
                    "_rebalance_rows": [],
                }
            current["_rows"].append(row)
            if is_entry:
                current["entry_date"] = current.get("entry_date") or row.get("trade_date")
                current["_entry_rows"].append(row)
            elif is_rebalance:
                current["_rebalance_rows"].append(row)
            elif is_exit:
                current["exit_date"] = row.get("trade_date")
                current["_exit_rows"].append(row)
                lifecycles.append(_finalize_lifecycle(current))
                current = None
        if current is not None:
            current["exit_date"] = current.get("exit_date")
            lifecycles.append(_finalize_lifecycle(current))
    return pd.DataFrame(lifecycles)


def summarize_lifecycle_costs(lifecycle_df: pd.DataFrame) -> dict:
    """Resumir entrada vs saida vs rebalanceamento."""
    if lifecycle_df is None or lifecycle_df.empty:
        return {
            "status": "INSUFFICIENT_DATA",
            "avg_entry_cost": 0.0,
            "avg_exit_cost": 0.0,
            "avg_rebalance_cost": 0.0,
            "entry_cost_pct": 0.0,
            "exit_cost_pct": 0.0,
            "rebalance_cost_pct": 0.0,
            "dominant_lifecycle": None,
            "affected_tickers": [],
        }
    total = pd.to_numeric(lifecycle_df["total_cost"], errors="coerce").fillna(0).sum()
    entry = pd.to_numeric(lifecycle_df["entry_cost"], errors="coerce").fillna(0)
    exit_ = pd.to_numeric(lifecycle_df["exit_cost"], errors="coerce").fillna(0)
    rebalance = pd.to_numeric(lifecycle_df["rebalance_cost"], errors="coerce").fillna(0)
    dominant = lifecycle_df.sort_values("total_cost", ascending=False).iloc[0].to_dict()
    affected = (
        lifecycle_df.groupby("ticker")["total_cost"].sum().sort_values(ascending=False).head(10).reset_index().to_dict("records")
        if "ticker" in lifecycle_df.columns
        else []
    )
    return {
        "status": "OK",
        "avg_entry_cost": float(entry.mean()) if len(entry) else 0.0,
        "avg_exit_cost": float(exit_.mean()) if len(exit_) else 0.0,
        "avg_rebalance_cost": float(rebalance.mean()) if len(rebalance) else 0.0,
        "entry_cost_pct": float(entry.sum() / total) if total else 0.0,
        "exit_cost_pct": float(exit_.sum() / total) if total else 0.0,
        "rebalance_cost_pct": float(rebalance.sum() / total) if total else 0.0,
        "dominant_lifecycle": dominant.get("lifecycle_id"),
        "affected_tickers": affected,
    }
