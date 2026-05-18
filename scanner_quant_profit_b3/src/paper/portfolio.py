"""Engine de carteira simulada."""
from __future__ import annotations

import math
from uuid import uuid4

import pandas as pd

from src.paper.order_model import PaperOrder, PaperPortfolio, PaperPosition


def initialize_portfolio(capital) -> PaperPortfolio:
    cap = float(capital)
    return PaperPortfolio(portfolio_id=str(uuid4()), capital_initial=cap, cash=cap, equity=cap)


def apply_order(portfolio: PaperPortfolio, order: PaperOrder) -> PaperPortfolio:
    if order.status != "SIMULATED_FILLED" or not order.simulated_execution_price or order.quantity <= 0:
        return portfolio
    side = order.side.upper()
    px = float(order.simulated_execution_price)
    qty = float(order.quantity)
    costs = float(order.execution_cost or 0) + float(order.slippage_cost or 0)
    pos = portfolio.positions.get(order.ticker)
    if side == "BUY":
        total = px * qty + costs
        if total > portfolio.cash:
            return portfolio
        if pos:
            new_qty = pos.quantity + qty
            pos.avg_price = (pos.avg_price * pos.quantity + px * qty) / new_qty
            pos.quantity = new_qty
        else:
            pos = PaperPosition(ticker=order.ticker, quantity=qty, avg_price=px, market_price=px)
            portfolio.positions[order.ticker] = pos
        portfolio.cash -= total
    elif side in {"SELL", "CLOSE", "REDUCE"} and pos:
        sell_qty = min(qty, pos.quantity)
        proceeds = px * sell_qty - costs
        pos.realized_pnl += (px - pos.avg_price) * sell_qty - costs
        pos.quantity -= sell_qty
        portfolio.cash += proceeds
        if pos.quantity <= 0:
            del portfolio.positions[order.ticker]
    return portfolio


def mark_to_market(portfolio: PaperPortfolio, prices_df: pd.DataFrame, trade_date: str | None = None) -> PaperPortfolio:
    work = prices_df.copy()
    if trade_date and "trade_date" in work.columns:
        work = work[work["trade_date"].astype(str) == str(trade_date)]
    prices = work.sort_values("trade_date").groupby("ticker").tail(1).set_index("ticker") if not work.empty else pd.DataFrame()
    exposure = 0.0
    unrealized = 0.0
    for ticker, pos in list(portfolio.positions.items()):
        if ticker in prices.index:
            pos.market_price = float(pd.to_numeric(pd.Series([prices.loc[ticker].get("close")]), errors="coerce").iloc[0])
        pos.market_value = pos.quantity * pos.market_price
        pos.unrealized_pnl = (pos.market_price - pos.avg_price) * pos.quantity
        exposure += abs(pos.market_value)
        unrealized += pos.unrealized_pnl
    portfolio.exposure = exposure
    portfolio.equity = portfolio.cash + sum(p.market_value for p in portfolio.positions.values())
    portfolio.leverage = exposure / portfolio.equity if portfolio.equity else math.nan
    return portfolio


def calculate_portfolio_exposure(portfolio: PaperPortfolio) -> float:
    return float(sum(abs(p.market_value) for p in portfolio.positions.values()))


def calculate_portfolio_pnl(portfolio: PaperPortfolio) -> dict:
    realized = sum(p.realized_pnl for p in portfolio.positions.values())
    unrealized = sum(p.unrealized_pnl for p in portfolio.positions.values())
    return {"realized_pnl": realized, "unrealized_pnl": unrealized, "total_pnl": realized + unrealized}


def calculate_portfolio_drawdown(equity_curve) -> pd.Series:
    equity = pd.to_numeric(pd.Series(equity_curve), errors="coerce")
    return equity / equity.cummax() - 1


def calculate_portfolio_var(portfolio: PaperPortfolio, risk_snapshots: pd.DataFrame) -> dict:
    if risk_snapshots is None or risk_snapshots.empty:
        portfolio.var_95 = 0.0
        portfolio.expected_shortfall_95 = 0.0
        return {"portfolio_var_95": 0.0, "portfolio_es_95": 0.0}
    risk = risk_snapshots.sort_values("trade_date").groupby("ticker").tail(1).set_index("ticker")
    var_total = 0.0
    es_total = 0.0
    for ticker, pos in portfolio.positions.items():
        if ticker not in risk.index:
            continue
        base_value = float(risk.loc[ticker].get("recommended_position_value") or risk.loc[ticker].get("position_value") or pos.market_value or 0)
        scale = abs(pos.market_value) / base_value if base_value else 0
        pos.var_95 = float(risk.loc[ticker].get("parametric_var_95") or risk.loc[ticker].get("var_95") or 0) * scale
        pos.expected_shortfall_95 = float(risk.loc[ticker].get("expected_shortfall_95") or 0) * scale
        pos.risk_status = str(risk.loc[ticker].get("risk_status") or "DADOS_INSUFICIENTES")
        var_total += pos.var_95
        es_total += pos.expected_shortfall_95
    portfolio.var_95 = var_total
    portfolio.expected_shortfall_95 = es_total
    return {"portfolio_var_95": var_total, "portfolio_es_95": es_total}


def calculate_portfolio_risk_summary(portfolio: PaperPortfolio) -> dict:
    return {
        "equity": portfolio.equity,
        "cash": portfolio.cash,
        "exposure": portfolio.exposure,
        "leverage": portfolio.leverage,
        "positions_count": len(portfolio.positions),
        "portfolio_var_95": portfolio.var_95,
        "portfolio_es_95": portfolio.expected_shortfall_95,
    }

