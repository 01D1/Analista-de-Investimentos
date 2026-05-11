"""Custos operacionais, slippage e qualidade de execução."""
from __future__ import annotations

import math
from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        number = float(value)
        return default if math.isnan(number) else number
    except (TypeError, ValueError):
        return default


def calculate_b3_costs(
    gross_value: Any,
    brokerage: float = 0.0,
    b3_fee_bps: float = 3.25,
    tax_bps: float = 0.0,
) -> dict:
    """Calcula custo financeiro estimado em uma ponta da operação."""
    value = max(_to_float(gross_value), 0.0)
    variable_bps = max(_to_float(b3_fee_bps), 0.0) + max(_to_float(tax_bps), 0.0)
    variable_cost = value * variable_bps / 10_000.0
    fixed_cost = max(_to_float(brokerage), 0.0)
    total = variable_cost + fixed_cost
    pct = (total / value * 100.0) if value else 0.0
    return {
        "gross_value": round(value, 4),
        "cost_value": round(total, 4),
        "cost_pct": round(pct, 4),
        "cost_bps": round(pct * 100.0, 4),
    }


def calculate_slippage(price: Any, slippage_bps: float = 5.0, side: str = "buy") -> float:
    """Ajusta preço teórico por slippage estimado."""
    price_f = _to_float(price)
    factor = max(_to_float(slippage_bps), 0.0) / 10_000.0
    side_norm = str(side).lower()
    if side_norm in {"buy", "compra", "cover"}:
        adjusted = price_f * (1.0 + factor)
    elif side_norm in {"sell", "venda", "short"}:
        adjusted = price_f * (1.0 - factor)
    else:
        raise ValueError("side deve ser 'buy' ou 'sell'")
    return round(adjusted, 6)


def calculate_round_trip_return(
    entry_price: Any,
    exit_price: Any,
    side: str = "long",
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
) -> dict:
    """Calcula retorno bruto e líquido de uma operação completa."""
    entry = _to_float(entry_price)
    exit_ = _to_float(exit_price)
    if entry <= 0:
        return {
            "entry_price_theoretical": entry,
            "exit_price_theoretical": exit_,
            "entry_price_executed": entry,
            "exit_price_executed": exit_,
            "gross_return": 0.0,
            "net_return": 0.0,
            "total_cost_pct": 0.0,
            "total_slippage_pct": 0.0,
        }

    side_norm = str(side).lower()
    if side_norm == "long":
        entry_exec = calculate_slippage(entry, slippage_bps, side="buy")
        exit_exec = calculate_slippage(exit_, slippage_bps, side="sell")
        gross_return = (exit_ / entry - 1.0) * 100.0
        net_before_cost = (exit_exec / entry_exec - 1.0) * 100.0
    elif side_norm == "short":
        entry_exec = calculate_slippage(entry, slippage_bps, side="sell")
        exit_exec = calculate_slippage(exit_, slippage_bps, side="buy")
        gross_return = (entry / exit_ - 1.0) * 100.0 if exit_ else 0.0
        net_before_cost = (entry_exec / exit_exec - 1.0) * 100.0 if exit_exec else 0.0
    else:
        raise ValueError("side deve ser 'long' ou 'short'")

    total_cost_pct = max(_to_float(cost_bps), 0.0) * 2.0 / 100.0
    total_slippage_pct = max(_to_float(slippage_bps), 0.0) * 2.0 / 100.0
    net_return = net_before_cost - total_cost_pct
    return {
        "entry_price_theoretical": round(entry, 6),
        "exit_price_theoretical": round(exit_, 6),
        "entry_price_executed": round(entry_exec, 6),
        "exit_price_executed": round(exit_exec, 6),
        "gross_return": round(gross_return, 4),
        "net_return": round(net_return, 4),
        "total_cost_pct": round(total_cost_pct, 4),
        "total_slippage_pct": round(total_slippage_pct, 4),
    }


def estimate_liquidity_penalty(
    volume: Any,
    trades: Any | None = None,
    min_volume: float = 5_000_000,
    min_trades: int = 500,
) -> dict:
    """Estima penalidade percentual por liquidez baixa."""
    volume_f = max(_to_float(volume), 0.0)
    trades_f = max(_to_float(trades, default=min_trades), 0.0)
    vol_ratio = volume_f / min_volume if min_volume else 1.0
    trades_ratio = trades_f / min_trades if min_trades else 1.0
    weakest = min(vol_ratio, trades_ratio)
    if weakest >= 1.0:
        penalty = 0.0
    elif weakest >= 0.5:
        penalty = 0.10
    elif weakest >= 0.2:
        penalty = 0.25
    else:
        penalty = 0.50
    return {
        "volume_ratio": round(vol_ratio, 4),
        "trades_ratio": round(trades_ratio, 4),
        "penalty_pct": round(penalty, 4),
        "passes_liquidity": bool(volume_f >= min_volume and trades_f >= min_trades),
    }


def classify_execution_quality(volume: Any, trades: Any | None = None, spread_pct: Any | None = None) -> str:
    """Classifica qualidade operacional por volume, negócios e spread."""
    volume_f = _to_float(volume)
    trades_f = _to_float(trades, default=1_000)
    spread = _to_float(spread_pct, default=0.0)

    if volume_f < 500_000 or trades_f < 50 or spread > 3.0:
        return "INVIAVEL"
    if volume_f < 2_000_000 or trades_f < 250 or spread > 1.2:
        return "RUIM"
    if volume_f < 10_000_000 or trades_f < 1_000 or spread > 0.6:
        return "ACEITAVEL"
    if volume_f < 50_000_000 or trades_f < 10_000 or spread > 0.15:
        return "BOA"
    return "EXCELENTE"
