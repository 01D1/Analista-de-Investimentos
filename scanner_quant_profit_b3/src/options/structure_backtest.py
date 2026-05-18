"""Backtest preliminar de estruturas de opções usando snapshots históricos."""
from __future__ import annotations

import json
import math
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.options.expiration_engine import handle_expired_structure
from src.options.options_execution_costs import calculate_leg_execution_price, calculate_structure_execution_costs, classify_structure_execution_quality
from src.options.options_history import create_daily_chain_view
from src.options.structures import CONTRACT_SIZE


RESULT_COLUMNS = [
    "entry_date",
    "exit_date",
    "underlying",
    "structure_type",
    "maturity_date",
    "dte_entry",
    "dte_exit",
    "legs_json",
    "entry_debit",
    "entry_credit",
    "exit_value",
    "gross_pnl",
    "net_pnl",
    "gross_return",
    "net_return",
    "max_loss",
    "return_on_risk",
    "exit_reason",
    "liquidity_score",
    "spread_cost",
    "transaction_cost",
    "slippage_cost",
    "execution_quality",
    "status",
    "metadata_json",
]


def _empty_results() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def _leg_from_row(row: pd.Series, direction: str) -> dict[str, Any]:
    return {
        "option_ticker": str(row.get("option_ticker")),
        "option_type": str(row.get("option_type")),
        "direction": direction,
        "strike": _num(row.get("strike")),
        "price": _num(row.get("last_price")),
        "last_price": _num(row.get("last_price")),
        "bid": row.get("bid"),
        "ask": row.get("ask"),
        "quantity": 1,
        "volume": _num(row.get("volume")),
        "trades": _num(row.get("trades")),
        "financial_volume": _num(row.get("financial_volume")),
        "spread_pct": _num(row.get("spread_pct")),
        "moneyness_class": str(row.get("moneyness_class") or "UNKNOWN"),
        "liquidity_score": _num(row.get("liquidity_score")),
    }


def _structure_from_legs(structure_type: str, underlying: str, maturity_date: str, entry_date: str, dte_entry: int, legs: list[dict[str, Any]]) -> dict[str, Any]:
    debit = 0.0
    credit = 0.0
    for leg in legs:
        value = _num(leg.get("price")) * _num(leg.get("quantity"), 1) * CONTRACT_SIZE
        if leg.get("direction") == "BUY":
            debit += value
        else:
            credit += value
    max_loss = debit if debit > 0 else math.nan
    if structure_type in {"BULL_CALL_SPREAD", "BEAR_PUT_SPREAD"} and len(legs) == 2:
        width = abs(_num(legs[1].get("strike")) - _num(legs[0].get("strike"))) * CONTRACT_SIZE
        max_loss = max(debit - credit, 0)
        max_profit = max(width - max_loss, 0)
    elif structure_type == "LONG_CALL":
        max_profit = math.inf
    elif structure_type == "LONG_PUT":
        max_profit = max(_num(legs[0].get("strike")) * CONTRACT_SIZE - debit, 0)
    else:
        max_profit = math.nan
    return {
        "entry_date": entry_date,
        "underlying": underlying,
        "structure_type": structure_type,
        "maturity_date": maturity_date,
        "dte_entry": int(dte_entry),
        "legs": legs,
        "legs_json": json.dumps(legs, ensure_ascii=False),
        "entry_debit": round(debit, 6),
        "entry_credit": round(credit, 6),
        "max_loss": round(max_loss, 6) if math.isfinite(max_loss) else max_loss,
        "max_profit": max_profit,
        "liquidity_score": float(np.mean([_num(l.get("liquidity_score")) for l in legs])) if legs else 0.0,
    }


def generate_structure_entries(chain_df: pd.DataFrame, structure_type: str, rules: dict | None = None) -> pd.DataFrame:
    rules = rules or {}
    daily = create_daily_chain_view(chain_df)
    if daily.empty:
        return pd.DataFrame()
    work = daily.copy()
    structure_type = str(structure_type or "LONG_CALL").upper()
    if rules.get("underlyings"):
        allowed = [u.upper() for u in rules["underlyings"]]
        work = work[work["underlying"].astype(str).str.upper().isin(allowed)]
    work = work[pd.to_numeric(work["days_to_maturity"], errors="coerce").between(rules.get("min_dte", 7), rules.get("max_dte", 90))]
    work = work[pd.to_numeric(work["liquidity_score"], errors="coerce").fillna(0) >= rules.get("min_liquidity_score", 0)]
    work = work[pd.to_numeric(work["spread_pct"], errors="coerce").fillna(999) <= rules.get("max_spread_pct", 999)]
    work = work[pd.to_numeric(work["volume"], errors="coerce").fillna(0) >= rules.get("min_volume", 0)]
    work = work[pd.to_numeric(work["trades"], errors="coerce").fillna(0) >= rules.get("min_trades", 0)]
    target_moneyness = rules.get("target_moneyness")
    if target_moneyness:
        work = work[work["moneyness_class"].astype(str).str.upper() == str(target_moneyness).upper()]

    entries = []
    for (trade_date, underlying, maturity), group in work.groupby(["trade_date", "underlying", "maturity_date"], dropna=False):
        group = group.sort_values("strike")
        if structure_type == "LONG_CALL":
            calls = group[group["option_type"] == "CALL"]
            if not calls.empty:
                row = calls.iloc[len(calls) // 2]
                entries.append(_structure_from_legs(structure_type, underlying, maturity, trade_date, row.get("days_to_maturity"), [_leg_from_row(row, "BUY")]))
        elif structure_type == "LONG_PUT":
            puts = group[group["option_type"] == "PUT"]
            if not puts.empty:
                row = puts.iloc[len(puts) // 2]
                entries.append(_structure_from_legs(structure_type, underlying, maturity, trade_date, row.get("days_to_maturity"), [_leg_from_row(row, "BUY")]))
        elif structure_type == "BULL_CALL_SPREAD":
            calls = group[group["option_type"] == "CALL"].sort_values("strike")
            if len(calls) >= 2:
                entries.append(_structure_from_legs(structure_type, underlying, maturity, trade_date, calls.iloc[0].get("days_to_maturity"), [_leg_from_row(calls.iloc[0], "BUY"), _leg_from_row(calls.iloc[1], "SELL")]))
        elif structure_type == "BEAR_PUT_SPREAD":
            puts = group[group["option_type"] == "PUT"].sort_values("strike", ascending=False)
            if len(puts) >= 2:
                entries.append(_structure_from_legs(structure_type, underlying, maturity, trade_date, puts.iloc[0].get("days_to_maturity"), [_leg_from_row(puts.iloc[0], "BUY"), _leg_from_row(puts.iloc[1], "SELL")]))
    return pd.DataFrame(entries)


def _find_exit_date(daily: pd.DataFrame, entry_date: str, maturity_date: str, holding_days: int, exit_at_expiry: bool = False) -> tuple[str | None, str]:
    dates = pd.to_datetime(daily["trade_date"], errors="coerce").dropna().sort_values().unique()
    entry_ts = pd.Timestamp(entry_date)
    maturity_ts = pd.Timestamp(maturity_date)
    target = maturity_ts if exit_at_expiry else min(entry_ts + timedelta(days=int(holding_days)), maturity_ts)
    future = [pd.Timestamp(d) for d in dates if pd.Timestamp(d) > entry_ts and pd.Timestamp(d) >= target]
    if future:
        chosen = min(future)
        reason = "EXPIRY" if chosen.date() >= maturity_ts.date() else "HOLDING_DAYS"
        return str(chosen.date()), reason
    before_expiry = [pd.Timestamp(d) for d in dates if entry_ts < pd.Timestamp(d) <= maturity_ts]
    if before_expiry:
        chosen = max(before_expiry)
        return str(chosen.date()), "LAST_AVAILABLE_BEFORE_EXPIRY"
    return None, "MISSING_EXIT_DATA"


def simulate_structure_exit(chain_df: pd.DataFrame, structure_entry: dict | pd.Series, exit_rules: dict | None = None) -> dict[str, Any]:
    exit_rules = exit_rules or {}
    entry = structure_entry.to_dict() if hasattr(structure_entry, "to_dict") else dict(structure_entry)
    daily = create_daily_chain_view(chain_df)
    if daily.empty:
        return {"status": "OPEN", "exit_reason": "MISSING_EXIT_DATA"}
    exit_date, reason = _find_exit_date(daily, entry["entry_date"], entry["maturity_date"], exit_rules.get("holding_days", 5), exit_rules.get("exit_at_expiry", False))
    if not exit_date:
        return {"status": "OPEN", "exit_reason": reason}
    exit_rows = daily[daily["trade_date"].astype(str) == exit_date]
    legs = entry.get("legs") or json.loads(entry.get("legs_json") or "[]")
    exit_legs = []
    for leg in legs:
        row = exit_rows[exit_rows["option_ticker"].astype(str) == str(leg.get("option_ticker"))]
        if row.empty:
            return {"status": "SKIPPED_MISSING_DATA", "exit_date": exit_date, "exit_reason": "MISSING_LEG"}
        enriched = _leg_from_row(row.iloc[0], leg.get("direction"))
        exit_legs.append(enriched)
    return {
        "status": "COMPLETED",
        "exit_date": exit_date,
        "exit_reason": reason,
        "dte_exit": int(pd.to_numeric(exit_rows[exit_rows["option_ticker"].astype(str) == str(legs[0].get("option_ticker"))]["days_to_maturity"], errors="coerce").iloc[0]),
        "legs": exit_legs,
    }


def calculate_structure_pnl(entry_structure: dict | pd.Series, exit_structure: dict, cost_model: dict | None = None) -> dict[str, Any]:
    cost_model = cost_model or {}
    entry = entry_structure.to_dict() if hasattr(entry_structure, "to_dict") else dict(entry_structure)
    entry_legs = entry.get("legs") or json.loads(entry.get("legs_json") or "[]")
    exit_legs = exit_structure.get("legs") or []
    if not exit_legs:
        return {"status": exit_structure.get("status", "SKIPPED_MISSING_DATA")}
    slippage_bps = cost_model.get("slippage_bps", 5)
    cost_bps = cost_model.get("cost_bps", 10)

    entry_debit = 0.0
    entry_credit = 0.0
    exit_value = 0.0
    all_legs_for_quality = []
    for ent_leg, out_leg in zip(entry_legs, exit_legs):
        qty = _num(ent_leg.get("quantity"), 1) * CONTRACT_SIZE
        if ent_leg.get("direction") == "BUY":
            entry_price = calculate_leg_execution_price(ent_leg, "buy", True, slippage_bps)["price"]
            exit_price = calculate_leg_execution_price(out_leg, "sell", True, slippage_bps)["price"]
            entry_debit += entry_price * qty
            exit_value += exit_price * qty
        else:
            entry_price = calculate_leg_execution_price(ent_leg, "sell", True, slippage_bps)["price"]
            exit_price = calculate_leg_execution_price(out_leg, "buy", True, slippage_bps)["price"]
            entry_credit += entry_price * qty
            exit_value -= exit_price * qty
        if math.isnan(entry_price) or math.isnan(exit_price):
            return {"status": "SKIPPED_MISSING_DATA"}
        all_legs_for_quality.extend([ent_leg, out_leg])

    entry_execution = calculate_structure_execution_costs({"legs": entry_legs}, cost_bps, slippage_bps)
    exit_execution = calculate_structure_execution_costs({"legs": exit_legs}, cost_bps, slippage_bps)
    transaction_cost = entry_execution["total_transaction_cost"] + exit_execution["total_transaction_cost"]
    slippage_cost = entry_execution["total_slippage_cost"] + exit_execution["total_slippage_cost"]
    spread_cost = entry_execution["spread_cost"] + exit_execution["spread_cost"]
    gross_pnl = exit_value - entry_debit + entry_credit
    net_pnl = gross_pnl - transaction_cost - slippage_cost
    capital = max(entry_debit - entry_credit, _num(entry.get("max_loss")), 1.0)
    return {
        "entry_debit": round(entry_debit, 6),
        "entry_credit": round(entry_credit, 6),
        "exit_value": round(exit_value, 6),
        "gross_pnl": round(gross_pnl, 6),
        "net_pnl": round(net_pnl, 6),
        "gross_return": round(gross_pnl / capital * 100, 6),
        "net_return": round(net_pnl / capital * 100, 6),
        "return_on_risk": round(net_pnl / capital * 100, 6),
        "spread_cost": round(spread_cost, 6),
        "transaction_cost": round(transaction_cost, 6),
        "slippage_cost": round(slippage_cost, 6),
        "execution_quality": classify_structure_execution_quality(all_legs_for_quality),
        "status": "COMPLETED",
    }


def run_structure_backtest(
    chain_df: pd.DataFrame,
    structure_type: str,
    rules: dict | None = None,
    exit_rules: dict | None = None,
    cost_model: dict | None = None,
) -> pd.DataFrame:
    entries = generate_structure_entries(chain_df, structure_type, rules)
    if entries.empty:
        return _empty_results()
    rows = []
    for _, entry in entries.iterrows():
        exit_info = simulate_structure_exit(chain_df, entry, exit_rules)
        if exit_info.get("status") != "COMPLETED":
            row = {c: pd.NA for c in RESULT_COLUMNS}
            row.update(entry.to_dict())
            row.update({"status": exit_info.get("status"), "exit_reason": exit_info.get("exit_reason"), "metadata_json": json.dumps({}, ensure_ascii=False)})
            rows.append(row)
            continue
        pnl = calculate_structure_pnl(entry, exit_info, cost_model)
        row = {
            "entry_date": entry["entry_date"],
            "exit_date": exit_info["exit_date"],
            "underlying": entry["underlying"],
            "structure_type": entry["structure_type"],
            "maturity_date": entry["maturity_date"],
            "dte_entry": entry["dte_entry"],
            "dte_exit": exit_info.get("dte_exit"),
            "legs_json": entry["legs_json"],
            "max_loss": entry.get("max_loss"),
            "exit_reason": exit_info.get("exit_reason"),
            "liquidity_score": entry.get("liquidity_score"),
            "metadata_json": json.dumps({}, ensure_ascii=False),
        }
        row.update(pnl)
        rows.append(row)
    out = pd.DataFrame(rows)
    for col in RESULT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[RESULT_COLUMNS]
