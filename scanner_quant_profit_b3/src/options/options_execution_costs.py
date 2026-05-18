"""Custos e qualidade de execução por perna em estruturas de opções."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from src.options.structures import CONTRACT_SIZE


def _num(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else math.nan
    except (TypeError, ValueError):
        return math.nan


def calculate_leg_execution_price(leg: dict | pd.Series, side: str, use_bid_ask: bool = True, slippage_bps: float = 0) -> dict[str, Any]:
    get = leg.get if hasattr(leg, "get") else lambda k, default=None: getattr(leg, k, default)
    side = str(side).lower()
    bid = _num(get("bid"))
    ask = _num(get("ask"))
    last = _num(get("last_price", get("price")))
    flag = "OK"
    if use_bid_ask and side == "buy" and not math.isnan(ask) and ask > 0:
        price = ask
    elif use_bid_ask and side == "sell" and not math.isnan(bid) and bid > 0:
        price = bid
    elif not math.isnan(last) and last > 0:
        adj = slippage_bps / 10_000
        price = last * (1 + adj if side == "buy" else 1 - adj)
        flag = "LAST_FALLBACK"
    else:
        return {"price": math.nan, "flag": "DADOS_INSUFICIENTES"}
    return {"price": round(float(price), 6), "flag": flag}


def classify_structure_execution_quality(legs) -> str:
    if legs is None or len(legs) == 0:
        return "DADOS_INSUFICIENTES"
    spreads = []
    volumes = []
    trades = []
    financial = []
    for leg in legs:
        get = leg.get if hasattr(leg, "get") else lambda k, default=None: getattr(leg, k, default)
        spreads.append(_num(get("spread_pct")))
        volumes.append(_num(get("volume")))
        trades.append(_num(get("trades")))
        financial.append(_num(get("financial_volume")))
    if any(math.isnan(x) for x in spreads):
        return "DADOS_INSUFICIENTES"
    max_spread = max(spreads)
    min_volume = np.nanmin(volumes) if volumes else 0
    min_trades = np.nanmin(trades) if trades else 0
    min_financial = np.nanmin(financial) if financial else 0
    if max_spread <= 3 and min_financial >= 1_000_000 and min_trades >= 200:
        return "EXCELENTE"
    if max_spread <= 8 and min_financial >= 250_000 and min_trades >= 50:
        return "BOA"
    if max_spread <= 15 and min_financial >= 50_000 and min_trades >= 10:
        return "ACEITAVEL"
    if max_spread <= 30 and min_volume > 0:
        return "RUIM"
    return "INVIAVEL"


def calculate_structure_execution_costs(structure: dict, cost_bps: float = 10, slippage_bps: float = 5) -> dict[str, Any]:
    legs = structure.get("legs") or []
    if not legs:
        return {
            "total_transaction_cost": 0.0,
            "total_slippage_cost": 0.0,
            "spread_cost": 0.0,
            "estimated_execution_value": math.nan,
            "execution_quality": "DADOS_INSUFICIENTES",
        }
    gross_value = 0.0
    spread_cost = 0.0
    for leg in legs:
        qty = abs(float(leg.get("quantity", 1))) * CONTRACT_SIZE
        side = "buy" if leg.get("direction") == "BUY" else "sell"
        exec_price = calculate_leg_execution_price(leg, side, True, slippage_bps)["price"]
        if math.isnan(exec_price):
            continue
        gross_value += abs(exec_price) * qty
        bid = _num(leg.get("bid"))
        ask = _num(leg.get("ask"))
        last = _num(leg.get("last_price", leg.get("price")))
        if not math.isnan(bid) and not math.isnan(ask) and not math.isnan(last):
            spread_cost += max(ask - bid, 0) * qty / 2
    return {
        "total_transaction_cost": round(gross_value * cost_bps / 10_000, 6),
        "total_slippage_cost": round(gross_value * slippage_bps / 10_000, 6),
        "spread_cost": round(spread_cost, 6),
        "estimated_execution_value": round(gross_value, 6),
        "execution_quality": classify_structure_execution_quality(legs),
    }

