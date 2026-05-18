"""Tratamento econômico simples de vencimento de opções."""
from __future__ import annotations

import json
from typing import Any

from src.options.structures import CONTRACT_SIZE


def calculate_option_expiration_value(option_type: str, underlying_price_at_expiry: float, strike: float) -> float:
    opt = str(option_type or "").upper()
    S = float(underlying_price_at_expiry or 0)
    K = float(strike or 0)
    if opt == "CALL":
        return max(S - K, 0)
    if opt == "PUT":
        return max(K - S, 0)
    return 0.0


def calculate_structure_expiration_value(structure: dict[str, Any], underlying_price_at_expiry: float) -> float:
    legs = structure.get("legs")
    if legs is None:
        legs = json.loads(structure.get("legs_json") or "[]")
    value = 0.0
    for leg in legs:
        intrinsic = calculate_option_expiration_value(leg.get("option_type"), underlying_price_at_expiry, leg.get("strike"))
        sign = 1 if leg.get("direction") == "BUY" else -1
        value += sign * intrinsic * float(leg.get("quantity", 1)) * CONTRACT_SIZE
    return round(value, 6)


def handle_expired_structure(structure: dict[str, Any], expiry_price: float) -> dict[str, Any]:
    final_value = calculate_structure_expiration_value(structure, expiry_price)
    entry_debit = float(structure.get("entry_debit", structure.get("net_debit", 0)) or 0)
    entry_credit = float(structure.get("entry_credit", structure.get("net_credit", 0)) or 0)
    pnl = final_value - entry_debit + entry_credit
    note = "Expiração sem valor econômico" if final_value <= 0 else "Expiração com valor intrínseco econômico"
    return {
        "final_value": final_value,
        "pnl_at_expiry": round(pnl, 6),
        "expired_otm": final_value <= 0,
        "has_intrinsic_value": final_value > 0,
        "notes": note,
    }

