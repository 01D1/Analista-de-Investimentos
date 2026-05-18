"""Controles de risco para carteira simulada."""
from __future__ import annotations

import pandas as pd


def check_max_positions(portfolio, max_positions: int) -> dict:
    ok = len(portfolio.positions) < int(max_positions)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_MAX_POSITIONS", "message": "Limite de posições simulado."}


def check_max_exposure(portfolio, max_exposure_pct: float) -> dict:
    exposure_pct = portfolio.exposure / portfolio.equity if portfolio.equity else 0
    ok = exposure_pct <= float(max_exposure_pct)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_EXPOSURE", "message": f"Exposição simulada {exposure_pct:.2%}."}


def check_max_asset_weight(portfolio, max_asset_weight_pct: float) -> dict:
    if not portfolio.positions or not portfolio.equity:
        return {"status": "PAPER_RISK_OK", "message": "Sem posições simuladas."}
    top = max(abs(p.market_value) / portfolio.equity for p in portfolio.positions.values())
    ok = top <= float(max_asset_weight_pct)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_EXPOSURE", "message": f"Maior peso simulado {top:.2%}."}


def check_daily_loss_limit(portfolio, daily_loss_limit_pct: float) -> dict:
    loss = max(0.0, portfolio.capital_initial - portfolio.equity)
    ok = loss / portfolio.capital_initial <= float(daily_loss_limit_pct)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_DRAWDOWN", "message": "Limite diário simulado."}


def check_drawdown_limit(portfolio, max_drawdown_pct: float) -> dict:
    ok = abs(float(portfolio.drawdown or 0)) <= float(max_drawdown_pct)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_DRAWDOWN", "message": "Drawdown simulado."}


def check_var_limit(portfolio, max_portfolio_var_pct: float) -> dict:
    var_pct = portfolio.var_95 / portfolio.equity if portfolio.equity else 0
    ok = var_pct <= float(max_portfolio_var_pct)
    return {"status": "PAPER_RISK_OK" if ok else "PAPER_BLOCKED_VAR", "message": f"VaR simulado {var_pct:.2%}."}


def evaluate_paper_trade_risk(order, portfolio, risk_snapshot) -> dict:
    if risk_snapshot is None or (hasattr(risk_snapshot, "empty") and risk_snapshot.empty):
        return {"status": "PAPER_BLOCKED_DATA", "message": "Risco insuficiente para ordem simulada."}
    if hasattr(risk_snapshot, "iloc"):
        row = risk_snapshot.iloc[0]
    else:
        row = risk_snapshot
    risk_status = str(row.get("risk_status", "")).upper()
    if "BLOCKED" in risk_status:
        return {"status": "PAPER_BLOCKED_VAR", "message": "Risk Engine bloqueou o ativo para estudo."}
    liquidity = pd.to_numeric(pd.Series([row.get("recommended_size")]), errors="coerce").iloc[0]
    if pd.notna(liquidity) and float(order.quantity) > float(liquidity) * 1.5:
        return {"status": "PAPER_BLOCKED_LIQUIDITY", "message": "Quantidade acima do sizing analítico."}
    return {"status": "PAPER_RISK_OK", "message": "Risco da ordem simulada dentro dos limites analíticos."}

