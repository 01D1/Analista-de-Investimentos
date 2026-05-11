"""Métricas puras para opções da B3."""
from __future__ import annotations

from typing import Any

from .liquidity import liquidity_profile
from .metrics import pct_change, safe_divide, to_float
from .options_math import days_to_expiration


def _moneyness(spot: float, strike: float, option_type: str) -> str:
    if spot <= 0 or strike <= 0:
        return "INDEFINIDO"
    diff_pct = abs((spot / strike - 1.0) * 100.0)
    if diff_pct <= 2.0:
        return "ATM"
    if option_type.upper() == "CALL":
        return "ITM" if spot > strike else "OTM"
    return "ITM" if spot < strike else "OTM"


def option_metrics(
    *,
    underlying_price: Any,
    option_price: Any,
    strike: Any,
    option_type: str,
    trade_date: Any,
    expiration_date: Any,
    bid: Any | None = None,
    ask: Any | None = None,
    volume: Any = 0,
    trades: Any = 0,
    open_interest: Any | None = None,
) -> dict:
    spot = to_float(underlying_price, 0.0)
    price = to_float(option_price, 0.0)
    strike_f = to_float(strike, 0.0)
    otype = option_type.upper()

    if otype == "CALL":
        intrinsic = max(spot - strike_f, 0.0)
        moneyness_pct = pct_change(spot, strike_f, default=0.0)
    else:
        intrinsic = max(strike_f - spot, 0.0)
        moneyness_pct = pct_change(strike_f, spot, default=0.0)

    extrinsic = max(price - intrinsic, 0.0)
    bid_f = to_float(bid, 0.0)
    ask_f = to_float(ask, 0.0)
    mid = (bid_f + ask_f) / 2 if bid_f > 0 and ask_f > 0 else price
    spread_pct = safe_divide(ask_f - bid_f, mid, default=0.0) * 100.0 if mid > 0 else 0.0
    liq = liquidity_profile(
        volume=volume,
        trades=trades,
        spread_pct=spread_pct,
        min_volume=30_000,
        min_trades=5,
    )

    return {
        "option_type": otype,
        "underlying_price": spot,
        "option_price": price,
        "strike": strike_f,
        "days_to_maturity": days_to_expiration(trade_date, expiration_date),
        "moneyness": _moneyness(spot, strike_f, otype),
        "moneyness_pct": round(moneyness_pct, 4),
        "intrinsic_value": round(intrinsic, 4),
        "extrinsic_value": round(extrinsic, 4),
        "spread_pct": round(spread_pct, 4),
        "volume": to_float(volume, 0.0),
        "trades": to_float(trades, 0.0),
        "open_interest": None if open_interest is None else to_float(open_interest, 0.0),
        "liquidity_score": liq["liquidity_score"],
        "greeks_available": False,
        "greeks_limitation": "Greeks dependem de volatilidade implícita ou modelo externo quando não há IV observada.",
    }
