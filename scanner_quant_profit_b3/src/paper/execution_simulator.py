"""Simulador seguro de execução para ordens simuladas."""
from __future__ import annotations

import math

import pandas as pd


def simulate_market_order(price, side: str, slippage_bps: float = 5) -> dict:
    px = pd.to_numeric(pd.Series([price]), errors="coerce").iloc[0]
    if pd.isna(px) or float(px) <= 0:
        return {"simulated_execution_price": math.nan, "execution_cost": 0.0, "slippage_cost": 0.0, "execution_status": "DATA_INSUFFICIENT", "message": "Preço ausente para ordem simulada."}
    direction = 1 if str(side).upper() in {"BUY", "CLOSE_SHORT"} else -1
    slip = float(px) * float(slippage_bps) / 10_000
    exec_price = float(px) + direction * slip
    return {"simulated_execution_price": round(exec_price, 6), "execution_cost": 0.0, "slippage_cost": round(abs(slip), 6), "execution_status": "SIMULATED_FILLED", "message": "Ordem simulada a mercado."}


def simulate_limit_order(price, limit_price, side: str) -> dict:
    px = pd.to_numeric(pd.Series([price]), errors="coerce").iloc[0]
    limit = pd.to_numeric(pd.Series([limit_price]), errors="coerce").iloc[0]
    if pd.isna(px) or pd.isna(limit):
        return {"simulated_execution_price": math.nan, "execution_cost": 0.0, "slippage_cost": 0.0, "execution_status": "DATA_INSUFFICIENT", "message": "Preço/limite ausente."}
    side = str(side).upper()
    fill = (side == "BUY" and px <= limit) or (side in {"SELL", "CLOSE", "REDUCE"} and px >= limit)
    return {
        "simulated_execution_price": float(limit) if fill else math.nan,
        "execution_cost": 0.0,
        "slippage_cost": 0.0,
        "execution_status": "SIMULATED_FILLED" if fill else "SIMULATED_REJECTED",
        "message": "Ordem simulada limitada preenchida." if fill else "Preço não atingiu limite simulado.",
    }


def simulate_execution_from_ohlcv(row, order, cost_bps: float = 10, slippage_bps: float = 5, max_participation: float = 0.01) -> dict:
    close = row.get("close", row.get("price")) if hasattr(row, "get") else None
    volume = pd.to_numeric(pd.Series([row.get("volume") if hasattr(row, "get") else None]), errors="coerce").iloc[0]
    quantity = float(order.quantity if hasattr(order, "quantity") else order.get("quantity", 0))
    if quantity <= 0:
        return {"simulated_execution_price": math.nan, "execution_cost": 0.0, "slippage_cost": 0.0, "execution_status": "SIMULATED_REJECTED", "message": "Quantidade simulada inválida."}
    if pd.notna(volume) and volume > 0 and quantity > float(volume) * max_participation:
        return {"simulated_execution_price": math.nan, "execution_cost": 0.0, "slippage_cost": 0.0, "execution_status": "BLOCKED_LIQUIDITY", "message": "Participação simulada excede limite de liquidez."}
    if str(getattr(order, "order_type", "MARKET")).upper() == "LIMIT":
        result = simulate_limit_order(close, getattr(order, "theoretical_price", close), getattr(order, "side", "UNKNOWN"))
    else:
        result = simulate_market_order(close, getattr(order, "side", "UNKNOWN"), slippage_bps=slippage_bps)
    if result["execution_status"] == "SIMULATED_FILLED":
        gross = abs(float(result["simulated_execution_price"]) * quantity)
        result["execution_cost"] = round(gross * float(cost_bps) / 10_000, 6)
        result["slippage_cost"] = round(float(result["slippage_cost"]) * quantity, 6)
    result["cost_attribution_source"] = getattr(order, "cost_bucket", None) or getattr(order, "signal_source", "UNKNOWN")
    return result
