"""Diagnóstico de turnover no paper trading."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.paper.cost_structure_diagnostics import _metadata, _num


def _prepare(orders_df: pd.DataFrame) -> pd.DataFrame:
    work = orders_df.copy()
    work["trade_date"] = pd.to_datetime(work.get("trade_date"), errors="coerce")
    work["ticker"] = work.get("ticker", "UNKNOWN").fillna("UNKNOWN").astype(str).str.upper()
    work["signal_source"] = work.get("signal_source", "UNKNOWN").fillna("UNKNOWN").astype(str).str.lower()
    work["quantity"] = _num(work["quantity"] if "quantity" in work.columns else pd.Series(0, index=work.index))
    price = work["simulated_execution_price"] if "simulated_execution_price" in work.columns else work["theoretical_price"] if "theoretical_price" in work.columns else pd.Series(0, index=work.index)
    work["notional"] = (work["quantity"].abs() * _num(price)).fillna(0)
    work["exit_rule"] = work.apply(lambda r: _metadata(r).get("exit_rule_triggered") or _metadata(r).get("exit_reason") or r.get("side", "UNKNOWN"), axis=1).fillna("UNKNOWN").astype(str)
    work["holding_period"] = pd.to_numeric(work.apply(lambda r: _metadata(r).get("holding_period") or _metadata(r).get("holding_days") or 0, axis=1), errors="coerce").fillna(0)
    work["net_pnl"] = pd.to_numeric(work.apply(lambda r: _metadata(r).get("metadata_trade_pnl") or _metadata(r).get("trade_pnl") or 0, axis=1), errors="coerce").fillna(0)
    return work


def _group_turnover(work: pd.DataFrame, col: str) -> pd.DataFrame:
    columns = [col, "trades_count", "turnover", "net_pnl", "turnover_to_return_ratio", "turnover_flag", "metadata_json"]
    if work.empty or col not in work.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    for key, group in work.groupby(col, dropna=False):
        turnover = float(group["notional"].sum())
        pnl = float(group["net_pnl"].sum())
        ratio = turnover / max(abs(pnl), 1.0)
        rows.append(
            {
                col: key,
                "trades_count": int(len(group)),
                "turnover": round(turnover, 6),
                "net_pnl": round(pnl, 6),
                "turnover_to_return_ratio": round(ratio, 6),
                "turnover_flag": bool(ratio > 1000 or len(group) > 50),
                "metadata_json": "{}",
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("turnover", ascending=False).reset_index(drop=True)


def analyze_turnover(orders_df: pd.DataFrame, equity_curve_df: pd.DataFrame | None = None) -> dict[str, Any]:
    if orders_df is None or orders_df.empty:
        return {
            "summary": {
                "trades_per_day": 0.0,
                "average_holding_period": 0.0,
                "turnover_total": 0.0,
                "turnover_daily_avg": 0.0,
                "turnover_to_return_ratio": 0.0,
                "overtrading_flag": False,
                "stop_take_turnover_flag": False,
                "source_turnover_flag": False,
                "asset_turnover_flag": False,
                "metadata_json": "{}",
            },
            "turnover_by_ticker": pd.DataFrame(),
            "turnover_by_signal_source": pd.DataFrame(),
            "turnover_by_exit_rule": pd.DataFrame(),
        }
    work = _prepare(orders_df)
    days = int(work["trade_date"].dt.date.nunique()) if work["trade_date"].notna().any() else 1
    if equity_curve_df is not None and not equity_curve_df.empty and "trade_date" in equity_curve_df.columns:
        days = max(days, int(pd.to_datetime(equity_curve_df["trade_date"], errors="coerce").dt.date.nunique()))
    turnover = float(work["notional"].sum())
    pnl = float(work["net_pnl"].sum())
    by_ticker = _group_turnover(work, "ticker")
    by_source = _group_turnover(work, "signal_source")
    by_exit = _group_turnover(work, "exit_rule")
    trades_per_day = float(len(work) / max(days, 1))
    stop_take_mask = work["exit_rule"].astype(str).str.upper().str.contains("STOP|TAKE|LOSS|PROFIT", regex=True)
    summary = {
        "trades_per_day": round(trades_per_day, 6),
        "average_holding_period": round(float(work["holding_period"].replace(0, pd.NA).dropna().mean() or 0), 6),
        "turnover_total": round(turnover, 6),
        "turnover_daily_avg": round(float(turnover / max(days, 1)), 6),
        "turnover_to_return_ratio": round(float(turnover / max(abs(pnl), 1.0)), 6),
        "overtrading_flag": bool(trades_per_day > 5),
        "stop_take_turnover_flag": bool(stop_take_mask.mean() > 0.50) if len(work) else False,
        "source_turnover_flag": bool(by_source.get("turnover_flag", pd.Series(dtype=bool)).astype(bool).any()) if not by_source.empty else False,
        "asset_turnover_flag": bool(by_ticker.get("turnover_flag", pd.Series(dtype=bool)).astype(bool).any()) if not by_ticker.empty else False,
        "metadata_json": json.dumps({"days": days, "net_pnl": pnl}, ensure_ascii=False, default=str),
    }
    return {"summary": summary, "turnover_by_ticker": by_ticker, "turnover_by_signal_source": by_source, "turnover_by_exit_rule": by_exit}
