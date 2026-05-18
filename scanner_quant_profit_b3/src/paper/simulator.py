"""Simulador de paper trading/carteira simulada."""
from __future__ import annotations

import json
from uuid import uuid4

import pandas as pd

from src.paper.execution_simulator import simulate_execution_from_ohlcv
from src.paper.exit_rules import ExitRule, evaluate_exit_rules
from src.paper.loss_limits import check_daily_loss_limit, check_max_drawdown_limit, check_weekly_loss_limit
from src.paper.order_model import PaperOrder
from src.paper.performance import calculate_paper_performance
from src.paper.pnl_attribution import attribute_pnl_by_signal_source
from src.paper.portfolio import apply_order, calculate_portfolio_drawdown, calculate_portfolio_var, initialize_portfolio, mark_to_market
from src.paper.rebalancing import rebalance_portfolio_by_risk
from src.paper.risk_controls import check_max_positions, evaluate_paper_trade_risk


def _approved_signal(row) -> bool:
    values = " ".join(str(row.get(c, "")) for c in ["integrated_status", "integrated_governance_status", "technical_status", "setup_type", "signal_type", "governance_status", "quant_governance_status"])
    upper = values.upper()
    if "BLOQUEADO" in upper or "BLOCKED" in upper:
        return False
    if "APPROVED_FOR_STUDY" in upper or "APPROVED_FOR_REVIEW" in upper:
        return True
    return any(token in upper for token in ["ALTA_CONVERGENCIA_ANALITICA", "ASSIMETRIA_A_INVESTIGAR", "FORÇA", "OBSERVAR"])


def _price_for(prices_df: pd.DataFrame, ticker: str, trade_date: str):
    day = prices_df[(prices_df["ticker"].astype(str) == ticker) & (prices_df["trade_date"].astype(str) == str(trade_date))]
    return day.iloc[0] if not day.empty else None


def _risk_for(risk_df: pd.DataFrame | None, ticker: str):
    if risk_df is None or risk_df.empty:
        return pd.DataFrame()
    work = risk_df[risk_df["ticker"].astype(str) == ticker].copy()
    return work.tail(1)


def _order_row(order: PaperOrder, run_id=None) -> dict:
    data = order.to_dict()
    data["run_id"] = run_id
    data["order_status"] = data.pop("status")
    data.pop("order_id", None)
    return data


def _positions_rows(portfolio, trade_date: str, run_id=None) -> list[dict]:
    rows = []
    for pos in portfolio.positions.values():
        rows.append(
            {
                "run_id": run_id,
                "trade_date": trade_date,
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "market_price": pos.market_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
                "var_95": pos.var_95,
                "expected_shortfall_95": pos.expected_shortfall_95,
                "metadata_json": json.dumps({"risk_status": pos.risk_status}, ensure_ascii=False),
            }
        )
    return rows


def _equity_row(portfolio, trade_date: str, previous_equity: float, run_id=None) -> dict:
    daily_return = portfolio.equity / previous_equity - 1 if previous_equity else 0.0
    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "cash": portfolio.cash,
        "equity": portfolio.equity,
        "exposure": portfolio.exposure,
        "daily_return": daily_return,
        "drawdown": portfolio.drawdown,
        "portfolio_var_95": portfolio.var_95,
        "portfolio_es_95": portfolio.expected_shortfall_95,
        "metadata_json": "{}",
    }


def _build_default_exit_rules(
    stop_loss_pct=None,
    take_profit_pct=None,
    trailing_stop_pct=None,
    atr_stop_multiplier=None,
    fixed_holding_days=None,
) -> list[ExitRule]:
    rules: list[ExitRule] = []
    if stop_loss_pct:
        rules.append(ExitRule("stop_loss", "STOP_LOSS_PCT", True, 4, json.dumps({"stop_loss_pct": stop_loss_pct}), "Stop loss percentual simulado."))
    if atr_stop_multiplier:
        rules.append(ExitRule("atr_stop", "ATR_STOP", True, 4, json.dumps({"atr_multiplier": atr_stop_multiplier}), "ATR stop simulado."))
    if trailing_stop_pct:
        rules.append(ExitRule("trailing_stop", "TRAILING_STOP", True, 4, json.dumps({"trailing_stop_pct": trailing_stop_pct}), "Trailing stop simulado."))
    if take_profit_pct:
        rules.append(ExitRule("take_profit", "TAKE_PROFIT_PCT", True, 6, json.dumps({"take_profit_pct": take_profit_pct}), "Take profit percentual simulado."))
    if fixed_holding_days:
        rules.append(ExitRule("holding", "FIXED_HOLDING_DAYS", True, 8, json.dumps({"holding_days": fixed_holding_days}), "Saída por tempo simulada."))
    return rules


def _close_position(portfolio, ticker: str, trade_date: str, price_row, reason: str, rule: str, cost_bps: float, slippage_bps: float):
    pos = portfolio.positions.get(ticker)
    if pos is None:
        return portfolio, None, None
    order = PaperOrder(str(uuid4()), trade_date, ticker, "CLOSE", pos.quantity, float(price_row["close"]), signal_source="exit_rule")
    execution = simulate_execution_from_ohlcv(price_row, order, cost_bps=cost_bps, slippage_bps=slippage_bps)
    order.simulated_execution_price = execution["simulated_execution_price"]
    order.execution_cost = execution["execution_cost"]
    order.slippage_cost = execution["slippage_cost"]
    order.status = execution["execution_status"]
    order.rejection_reason = None if order.status == "SIMULATED_FILLED" else execution["message"]
    trade_pnl = 0.0
    if order.status == "SIMULATED_FILLED":
        trade_pnl = (float(order.simulated_execution_price) - pos.avg_price) * pos.quantity - order.execution_cost - order.slippage_cost
        order.metadata_json = json.dumps({"metadata_trade_pnl": trade_pnl, "exit_reason": reason, "exit_rule_triggered": rule, "signal_source": getattr(pos, "signal_source", "UNKNOWN")}, ensure_ascii=False)
        order.signal_source = getattr(pos, "signal_source", "exit_rule")
        portfolio = apply_order(portfolio, order)
    row = _order_row(order)
    row["metadata_trade_pnl"] = trade_pnl
    exit_event = {
        "run_id": None,
        "trade_date": trade_date,
        "ticker": ticker,
        "position_id": ticker,
        "exit_rule_triggered": rule,
        "exit_reason": reason,
        "exit_price": order.simulated_execution_price,
        "pnl": trade_pnl,
        "metadata_json": order.metadata_json,
    }
    return portfolio, row, exit_event


def run_paper_simulation(
    signals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: pd.DataFrame | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    capital: float = 100000,
    max_positions: int = 5,
    risk_pct: float = 0.005,
    allow_rebalance: bool = True,
    cost_bps: float = 10,
    slippage_bps: float = 5,
    exit_rules: list[ExitRule] | None = None,
    enable_rebalancing: bool = False,
    rebalance_frequency: str = "WEEKLY",
    use_regime_adjustment: bool = False,
    daily_loss_limit_pct: float | None = None,
    weekly_loss_limit_pct: float | None = None,
    max_drawdown_pct: float | None = None,
    trailing_stop_pct: float | None = None,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    atr_stop_multiplier: float | None = None,
) -> dict:
    if prices_df is None or prices_df.empty:
        empty = pd.DataFrame()
        return {"orders_df": empty, "positions_df": empty, "equity_curve_df": empty, "portfolio_snapshots_df": empty, "exit_events_df": empty, "rebalance_events_df": empty, "pnl_attribution_df": empty, "performance_summary": {"status": "INSUFFICIENT_DATA"}}
    prices = prices_df.copy()
    signals = signals_df.copy() if signals_df is not None else pd.DataFrame()
    for df in [prices, signals]:
        if not df.empty and "trade_date" in df.columns:
            df["trade_date"] = df["trade_date"].astype(str)
    if start_date:
        prices = prices[prices["trade_date"] >= str(start_date)]
        if not signals.empty:
            signals = signals[signals["trade_date"] >= str(start_date)]
    if end_date:
        prices = prices[prices["trade_date"] <= str(end_date)]
        if not signals.empty:
            signals = signals[signals["trade_date"] <= str(end_date)]
    if prices.empty:
        empty = pd.DataFrame()
        return {"orders_df": empty, "positions_df": empty, "equity_curve_df": empty, "portfolio_snapshots_df": empty, "exit_events_df": empty, "rebalance_events_df": empty, "pnl_attribution_df": empty, "performance_summary": {"status": "INSUFFICIENT_DATA"}}

    portfolio = initialize_portfolio(capital)
    order_rows = []
    position_rows = []
    equity_rows = []
    exit_events = []
    rebalance_events = []
    previous_equity = portfolio.equity
    dates = sorted(prices["trade_date"].dropna().astype(str).unique())
    rules = list(exit_rules or []) + _build_default_exit_rules(stop_loss_pct, take_profit_pct, trailing_stop_pct, atr_stop_multiplier)
    block_new_entries = False

    for day_index, trade_date in enumerate(dates):
        day_prices = prices[prices["trade_date"] == trade_date]
        portfolio = mark_to_market(portfolio, day_prices, trade_date)
        calculate_portfolio_var(portfolio, risk_df if risk_df is not None else pd.DataFrame())
        equity_tmp = pd.DataFrame(equity_rows + [_equity_row(portfolio, trade_date, previous_equity)])
        if not equity_tmp.empty:
            dd = calculate_portfolio_drawdown(equity_tmp["equity"]).iloc[-1]
            portfolio.drawdown = float(dd) if pd.notna(dd) else 0.0

        limit_checks = []
        if daily_loss_limit_pct:
            limit_checks.append(check_daily_loss_limit(equity_tmp, daily_loss_limit_pct))
        if weekly_loss_limit_pct:
            limit_checks.append(check_weekly_loss_limit(equity_tmp, weekly_loss_limit_pct))
        if max_drawdown_pct:
            limit_checks.append(check_max_drawdown_limit(equity_tmp, max_drawdown_pct))
        if any(item["limit_triggered"] for item in limit_checks):
            block_new_entries = True

        for ticker, pos in list(portfolio.positions.items()):
            price_row = _price_for(day_prices, ticker, trade_date)
            if price_row is None:
                continue
            pos.holding_days = int(getattr(pos, "holding_days", 0)) + 1
            if trailing_stop_pct:
                pos.trailing_stop = getattr(pos, "trailing_stop", None)
            risk_one = _risk_for(risk_df, ticker)
            risk_row = risk_one.iloc[0] if not risk_one.empty else None
            rules_to_eval = list(rules)
            if limit_checks and any(item["limit_triggered"] for item in limit_checks):
                rules_to_eval = [ExitRule("daily_loss", "DAILY_LOSS_EXIT", True, 2, json.dumps({"limits": limit_checks}), "Limite de perda simulado.")] + rules_to_eval
            exit_eval = evaluate_exit_rules(pos, price_row, risk_row=risk_row, rules=rules_to_eval)
            if not exit_eval["should_exit"] and limit_checks and any(item["limit_triggered"] for item in limit_checks):
                exit_eval = {"should_exit": True, "exit_reason": "Limite de perda simulado acionado.", "exit_rule_triggered": "DAILY_LOSS_EXIT", "exit_price_hint": price_row["close"], "metadata_json": json.dumps({"limits": limit_checks}, ensure_ascii=False)}
            if exit_eval["should_exit"]:
                portfolio, row, event = _close_position(portfolio, ticker, trade_date, price_row, exit_eval["exit_reason"], exit_eval["exit_rule_triggered"], cost_bps, slippage_bps)
                if row:
                    order_rows.append(row)
                if event:
                    exit_events.append(event)

        if enable_rebalancing and allow_rebalance and risk_df is not None and not risk_df.empty:
            do_rebalance = str(rebalance_frequency).upper() == "DAILY" or (str(rebalance_frequency).upper() == "WEEKLY" and day_index % 5 == 0)
            if do_rebalance:
                rebalance_orders = rebalance_portfolio_by_risk(portfolio, risk_df, day_prices)
                for _, reb in rebalance_orders.iterrows():
                    ticker = str(reb["ticker"]).upper()
                    price_row = _price_for(day_prices, ticker, trade_date)
                    if price_row is None:
                        continue
                    order = PaperOrder(str(uuid4()), trade_date, ticker, str(reb["side"]), float(reb["quantity"]), float(price_row["close"]), signal_source="rebalance")
                    execution = simulate_execution_from_ohlcv(price_row, order, cost_bps=cost_bps, slippage_bps=slippage_bps)
                    order.simulated_execution_price = execution["simulated_execution_price"]
                    order.execution_cost = execution["execution_cost"]
                    order.slippage_cost = execution["slippage_cost"]
                    order.status = execution["execution_status"]
                    order.rejection_reason = None if order.status == "SIMULATED_FILLED" else execution["message"]
                    portfolio = apply_order(portfolio, order)
                    order_rows.append(_order_row(order))
                    rebalance_events.append({"run_id": None, "trade_date": trade_date, "ticker": ticker, "action": order.side, "current_weight": reb.get("current_weight"), "target_weight": reb.get("target_weight"), "order_quantity": order.quantity, "reason": reb.get("reason"), "metadata_json": "{}"})

        day_signals = signals[signals["trade_date"] == trade_date] if not signals.empty else pd.DataFrame()
        for _, sig in day_signals.iterrows():
            ticker = str(sig.get("ticker", "")).upper()
            if block_new_entries:
                continue
            if not ticker or ticker in portfolio.positions:
                continue
            price_row = _price_for(prices, ticker, trade_date)
            if price_row is None:
                continue
            if not _approved_signal(sig):
                order = PaperOrder(str(uuid4()), trade_date, ticker, "BUY", 0, float(price_row["close"]), status="BLOCKED_GOVERNANCE", rejection_reason="Sinal bloqueado por governança.")
                order_rows.append(_order_row(order))
                continue
            max_check = check_max_positions(portfolio, max_positions)
            if max_check["status"] != "PAPER_RISK_OK":
                order = PaperOrder(str(uuid4()), trade_date, ticker, "BUY", 0, float(price_row["close"]), status="BLOCKED_RISK", rejection_reason=max_check["message"])
                order_rows.append(_order_row(order))
                continue
            risk_one = _risk_for(risk_df, ticker)
            risk_size = pd.to_numeric(risk_one.get("recommended_size"), errors="coerce").iloc[0] if not risk_one.empty and "recommended_size" in risk_one.columns else pd.NA
            fallback_size = int((portfolio.equity * risk_pct) / max(float(price_row["close"]) * 0.05, 0.01))
            quantity = max(0, int(risk_size if pd.notna(risk_size) and risk_size > 0 else fallback_size))
            order = PaperOrder(str(uuid4()), trade_date, ticker, "BUY", quantity, float(price_row["close"]), signal_source=str(sig.get("signal_source", "integrated")), signal_id=sig.get("id"))
            risk_check = evaluate_paper_trade_risk(order, portfolio, risk_one)
            if risk_check["status"] != "PAPER_RISK_OK" and not risk_one.empty:
                order.status = "BLOCKED_RISK"
                order.rejection_reason = risk_check["message"]
                order_rows.append(_order_row(order))
                continue
            execution = simulate_execution_from_ohlcv(price_row, order, cost_bps=cost_bps, slippage_bps=slippage_bps)
            order.simulated_execution_price = execution["simulated_execution_price"]
            order.execution_cost = execution["execution_cost"]
            order.slippage_cost = execution["slippage_cost"]
            order.status = execution["execution_status"]
            order.rejection_reason = None if order.status == "SIMULATED_FILLED" else execution["message"]
            portfolio = apply_order(portfolio, order)
            if order.status == "SIMULATED_FILLED" and ticker in portfolio.positions:
                portfolio.positions[ticker].entry_date = trade_date
                portfolio.positions[ticker].holding_days = 0
                portfolio.positions[ticker].signal_source = order.signal_source
                portfolio.positions[ticker].trailing_stop = None
            order_rows.append(_order_row(order))

        portfolio = mark_to_market(portfolio, day_prices, trade_date)
        calculate_portfolio_var(portfolio, risk_df if risk_df is not None else pd.DataFrame())
        equity_tmp = pd.DataFrame(equity_rows + [_equity_row(portfolio, trade_date, previous_equity)])
        if not equity_tmp.empty:
            dd = calculate_portfolio_drawdown(equity_tmp["equity"]).iloc[-1]
            portfolio.drawdown = float(dd) if pd.notna(dd) else 0.0
        equity_rows.append(_equity_row(portfolio, trade_date, previous_equity))
        position_rows.extend(_positions_rows(portfolio, trade_date))
        previous_equity = portfolio.equity

    if portfolio.positions:
        last_date = dates[-1]
        last_prices = prices[prices["trade_date"] == last_date]
        for ticker, pos in list(portfolio.positions.items()):
            price_row = _price_for(last_prices, ticker, last_date)
            if price_row is None:
                continue
            order = PaperOrder(str(uuid4()), last_date, ticker, "CLOSE", pos.quantity, float(price_row["close"]), signal_source="simulation_end")
            execution = simulate_execution_from_ohlcv(price_row, order, cost_bps=cost_bps, slippage_bps=slippage_bps)
            order.simulated_execution_price = execution["simulated_execution_price"]
            order.execution_cost = execution["execution_cost"]
            order.slippage_cost = execution["slippage_cost"]
            order.status = execution["execution_status"]
            trade_pnl = (float(order.simulated_execution_price) - pos.avg_price) * pos.quantity - order.execution_cost - order.slippage_cost if order.status == "SIMULATED_FILLED" else 0
            order.metadata_json = json.dumps({"metadata_trade_pnl": trade_pnl}, ensure_ascii=False)
            portfolio = apply_order(portfolio, order)
            row = _order_row(order)
            row["metadata_trade_pnl"] = trade_pnl
            order_rows.append(row)
        portfolio = mark_to_market(portfolio, last_prices, last_date)
        calculate_portfolio_var(portfolio, risk_df if risk_df is not None else pd.DataFrame())
        equity_rows.append(_equity_row(portfolio, last_date, previous_equity))

    orders_df = pd.DataFrame(order_rows)
    positions_df = pd.DataFrame(position_rows)
    equity_curve_df = pd.DataFrame(equity_rows)
    snapshots_df = equity_curve_df.copy()
    exit_events_df = pd.DataFrame(exit_events)
    rebalance_events_df = pd.DataFrame(rebalance_events)
    pnl_attribution_df = attribute_pnl_by_signal_source(orders_df, positions_df)
    summary = calculate_paper_performance(equity_curve_df, orders_df)
    summary.update(
        {
            "status": "COMPLETED" if not equity_curve_df.empty else "INSUFFICIENT_DATA",
            "capital_initial": float(capital),
            "capital_final": float(equity_curve_df["equity"].iloc[-1]) if not equity_curve_df.empty else float(capital),
            "trades_count": int((orders_df.get("order_status", pd.Series(dtype=str)).astype(str) == "SIMULATED_FILLED").sum()) if not orders_df.empty else 0,
            "exit_events_count": int(len(exit_events_df)),
            "rebalance_events_count": int(len(rebalance_events_df)),
            "advanced_rules": bool(rules or enable_rebalancing or daily_loss_limit_pct or weekly_loss_limit_pct or max_drawdown_pct),
        }
    )
    return {"orders_df": orders_df, "positions_df": positions_df, "equity_curve_df": equity_curve_df, "portfolio_snapshots_df": snapshots_df, "exit_events_df": exit_events_df, "rebalance_events_df": rebalance_events_df, "pnl_attribution_df": pnl_attribution_df, "performance_summary": summary}
