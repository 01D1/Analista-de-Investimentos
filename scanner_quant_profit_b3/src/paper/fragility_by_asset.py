"""Diagnostico de fragilidade por ativo em paper trading."""
from __future__ import annotations

import json

import pandas as pd

from src.paper.fragility_score import add_fragility_columns


def _extract_pnl(row) -> float:
    if "metadata_trade_pnl" in row and pd.notna(row.get("metadata_trade_pnl")):
        return float(pd.to_numeric(pd.Series([row.get("metadata_trade_pnl")]), errors="coerce").fillna(0).iloc[0])
    try:
        meta = json.loads(row.get("metadata_json") or "{}")
        return float(meta.get("metadata_trade_pnl", meta.get("trade_pnl", 0)) or 0)
    except (TypeError, json.JSONDecodeError, ValueError):
        return 0.0


def _filled_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    if orders_df is None or orders_df.empty:
        return pd.DataFrame()
    out = orders_df.copy()
    status = out.get("order_status", out.get("status", pd.Series(dtype=str))).astype(str)
    out = out[status == "SIMULATED_FILLED"].copy()
    if out.empty:
        return out
    out["trade_pnl"] = out.apply(_extract_pnl, axis=1)
    out["execution_cost"] = pd.to_numeric(out.get("execution_cost"), errors="coerce").fillna(0)
    out["slippage_cost"] = pd.to_numeric(out.get("slippage_cost"), errors="coerce").fillna(0)
    out["total_cost"] = out["execution_cost"] + out["slippage_cost"]
    out["ticker"] = out["ticker"].astype(str).str.upper()
    return out


def analyze_pnl_by_asset(orders_df: pd.DataFrame, positions_df: pd.DataFrame, equity_df: pd.DataFrame | None = None) -> pd.DataFrame:
    columns = ["ticker", "trades_count", "gross_pnl", "net_pnl", "win_rate", "avg_trade_return", "max_loss_trade", "max_gain_trade", "contribution_pct", "avg_slippage_cost", "avg_transaction_cost", "total_cost_drag", "drawdown_contribution", "fragility_score", "fragility_class", "metadata_json"]
    filled = _filled_orders(orders_df)
    if filled.empty:
        return pd.DataFrame(columns=columns)
    total_abs = max(float(filled["trade_pnl"].abs().sum()), 1.0)
    rows = []
    for ticker, group in filled.groupby("ticker"):
        pnl = pd.to_numeric(group["trade_pnl"], errors="coerce").fillna(0)
        costs = pd.to_numeric(group["execution_cost"], errors="coerce").fillna(0)
        slippage = pd.to_numeric(group["slippage_cost"], errors="coerce").fillna(0)
        net_pnl = float(pnl.sum())
        drawdown_contribution = 0.0
        if positions_df is not None and not positions_df.empty:
            pos = positions_df[positions_df["ticker"].astype(str).str.upper() == ticker]
            drawdown_contribution = abs(float(pd.to_numeric(pos.get("unrealized_pnl"), errors="coerce").fillna(0).min() or 0))
        rows.append(
            {
                "ticker": ticker,
                "trades_count": int(len(group)),
                "gross_pnl": round(float(pnl[pnl > 0].sum()), 6),
                "net_pnl": round(net_pnl, 6),
                "win_rate": round(float((pnl > 0).mean()), 6),
                "avg_trade_return": round(float(pnl.mean()), 6),
                "max_loss_trade": round(float(pnl.min()), 6),
                "max_gain_trade": round(float(pnl.max()), 6),
                "contribution_pct": round(float(net_pnl / total_abs), 6),
                "avg_slippage_cost": round(float(slippage.mean()), 6),
                "avg_transaction_cost": round(float(costs.mean()), 6),
                "total_cost_drag": round(float((costs + slippage).sum()), 6),
                "drawdown_contribution": round(drawdown_contribution, 6),
                "metadata_json": "{}",
            }
        )
    out = add_fragility_columns(pd.DataFrame(rows))
    return out[columns]


def generate_asset_fragility_report(asset_df: pd.DataFrame) -> str:
    if asset_df is None or asset_df.empty:
        return "Fragilidade por ativo indisponivel: dados insuficientes."
    worst = asset_df.sort_values("fragility_score", ascending=False).head(3)
    names = ", ".join(worst["ticker"].astype(str).tolist())
    return f"Fragilidade detectada em ativos com maior score: {names}. A leitura e analitica e nao recomenda operacao."
