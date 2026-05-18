"""Limites de perda para paper trading."""
from __future__ import annotations

import pandas as pd


def _empty(limit_type):
    return {"limit_triggered": False, "limit_type": limit_type, "current_loss": 0.0, "threshold": 0.0, "message": "Histórico insuficiente."}


def check_daily_loss_limit(equity_curve_df: pd.DataFrame, daily_loss_limit_pct: float) -> dict:
    if equity_curve_df is None or len(equity_curve_df) < 2:
        return _empty("DAILY_LOSS")
    equity = pd.to_numeric(equity_curve_df["equity"], errors="coerce")
    current_loss = equity.iloc[-1] / equity.iloc[-2] - 1 if equity.iloc[-2] else 0
    triggered = current_loss <= -abs(float(daily_loss_limit_pct))
    return {"limit_triggered": bool(triggered), "limit_type": "DAILY_LOSS", "current_loss": float(current_loss), "threshold": -abs(float(daily_loss_limit_pct)), "message": "Limite diário simulado acionado." if triggered else "Limite diário não acionado."}


def check_weekly_loss_limit(equity_curve_df: pd.DataFrame, weekly_loss_limit_pct: float) -> dict:
    if equity_curve_df is None or len(equity_curve_df) < 5:
        return _empty("WEEKLY_LOSS")
    equity = pd.to_numeric(equity_curve_df["equity"], errors="coerce")
    current_loss = equity.iloc[-1] / equity.iloc[-5] - 1 if equity.iloc[-5] else 0
    triggered = current_loss <= -abs(float(weekly_loss_limit_pct))
    return {"limit_triggered": bool(triggered), "limit_type": "WEEKLY_LOSS", "current_loss": float(current_loss), "threshold": -abs(float(weekly_loss_limit_pct)), "message": "Limite semanal simulado acionado." if triggered else "Limite semanal não acionado."}


def check_max_drawdown_limit(equity_curve_df: pd.DataFrame, max_drawdown_pct: float) -> dict:
    if equity_curve_df is None or equity_curve_df.empty:
        return _empty("MAX_DRAWDOWN")
    dd = pd.to_numeric(equity_curve_df.get("drawdown"), errors="coerce")
    current = float(dd.min()) if dd.notna().any() else 0.0
    triggered = current <= -abs(float(max_drawdown_pct))
    return {"limit_triggered": bool(triggered), "limit_type": "MAX_DRAWDOWN", "current_loss": current, "threshold": -abs(float(max_drawdown_pct)), "message": "Limite de drawdown simulado acionado." if triggered else "Limite de drawdown não acionado."}

