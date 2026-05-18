"""Métricas de performance para paper trading."""
from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_paper_performance(equity_curve_df: pd.DataFrame, orders_df: pd.DataFrame) -> dict:
    if equity_curve_df is None or equity_curve_df.empty:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "volatility": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_trade_return": 0.0,
            "turnover": 0.0,
            "exposure_avg": 0.0,
            "exposure_max": 0.0,
            "var_avg": 0.0,
            "es_avg": 0.0,
            "best_day": 0.0,
            "worst_day": 0.0,
        }
    eq = equity_curve_df.copy()
    equity = pd.to_numeric(eq["equity"], errors="coerce").ffill()
    returns = pd.to_numeric(eq.get("daily_return"), errors="coerce").fillna(0)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1) if len(equity) > 1 and equity.iloc[0] else 0.0
    vol = float(returns.std() * np.sqrt(252)) if len(returns) > 1 else 0.0
    downside = returns[returns < 0].std() * np.sqrt(252) if (returns < 0).any() else 0.0
    sharpe = float((returns.mean() * 252) / vol) if vol else 0.0
    sortino = float((returns.mean() * 252) / downside) if downside else 0.0
    drawdown = pd.to_numeric(eq.get("drawdown"), errors="coerce").fillna(0)
    orders = orders_df.copy() if orders_df is not None else pd.DataFrame()
    filled = orders[orders.get("order_status", orders.get("status", "")).astype(str) == "SIMULATED_FILLED"] if not orders.empty else pd.DataFrame()
    pnl = pd.to_numeric(filled.get("metadata_trade_pnl", pd.Series(dtype=float)), errors="coerce").dropna() if not filled.empty else pd.Series(dtype=float)
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = abs(pnl[pnl < 0].sum())
    return {
        "total_return": round(total_return, 6),
        "annualized_return": round(float(returns.mean() * 252), 6),
        "volatility": round(vol, 6),
        "sharpe": round(sharpe, 6),
        "sortino": round(sortino, 6),
        "max_drawdown": round(float(drawdown.min()), 6),
        "win_rate": round(float((pnl > 0).mean()), 6) if len(pnl) else 0.0,
        "profit_factor": round(float(gross_profit / gross_loss), 6) if gross_loss else (round(float(gross_profit), 6) if gross_profit else 0.0),
        "avg_trade_return": round(float(pnl.mean()), 6) if len(pnl) else 0.0,
        "turnover": int(len(filled)),
        "exposure_avg": round(float(pd.to_numeric(eq.get("exposure"), errors="coerce").fillna(0).mean()), 6),
        "exposure_max": round(float(pd.to_numeric(eq.get("exposure"), errors="coerce").fillna(0).max()), 6),
        "var_avg": round(float(pd.to_numeric(eq.get("portfolio_var_95"), errors="coerce").fillna(0).mean()), 6),
        "es_avg": round(float(pd.to_numeric(eq.get("portfolio_es_95"), errors="coerce").fillna(0).mean()), 6),
        "best_day": round(float(returns.max()), 6),
        "worst_day": round(float(returns.min()), 6),
    }


def summarize_trades(orders_df: pd.DataFrame) -> dict:
    if orders_df is None or orders_df.empty:
        return {"orders_count": 0, "filled_count": 0, "rejected_count": 0}
    status = orders_df.get("order_status", orders_df.get("status")).astype(str)
    return {"orders_count": int(len(orders_df)), "filled_count": int((status == "SIMULATED_FILLED").sum()), "rejected_count": int((status != "SIMULATED_FILLED").sum())}


def summarize_positions(positions_df: pd.DataFrame) -> dict:
    if positions_df is None or positions_df.empty:
        return {"positions_count": 0, "market_value": 0.0}
    latest = positions_df.sort_values("trade_date").groupby("ticker").tail(1)
    return {"positions_count": int((pd.to_numeric(latest["quantity"], errors="coerce") > 0).sum()), "market_value": float(pd.to_numeric(latest["market_value"], errors="coerce").fillna(0).sum())}
