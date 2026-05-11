"""Capacidade operacional por liquidez e sizing conservador."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return default if pd.isna(out) else out
    except (TypeError, ValueError):
        return default


def estimate_trade_capacity(volume: Any, participation_rate: float = 0.01) -> float:
    """Estima capacidade financeira usando percentual máximo do volume financeiro."""
    return round(max(_num(volume), 0.0) * max(_num(participation_rate), 0.0), 2)


def estimate_position_size_by_risk(
    capital: Any,
    risk_pct: float,
    entry_price: Any,
    stop_price: Any,
) -> dict:
    """Calcula quantidade teórica por risco financeiro."""
    capital_f = max(_num(capital), 0.0)
    entry = _num(entry_price)
    stop = _num(stop_price)
    risk_per_unit = abs(entry - stop)
    risk_amount = capital_f * max(_num(risk_pct), 0.0)
    if entry <= 0 or risk_per_unit <= 0 or risk_amount <= 0:
        return {
            "quantity": 0,
            "risk_per_unit": round(risk_per_unit, 6),
            "financial_value": 0.0,
            "risk_amount": round(risk_amount, 2),
        }
    quantity = int(risk_amount // risk_per_unit)
    return {
        "quantity": quantity,
        "risk_per_unit": round(risk_per_unit, 6),
        "financial_value": round(quantity * entry, 2),
        "risk_amount": round(quantity * risk_per_unit, 2),
    }


def estimate_position_size_by_capacity(capital: Any, desired_size: Any, capacity: Any) -> dict:
    """Limita tamanho financeiro desejado por capital e capacidade de liquidez."""
    capital_f = max(_num(capital), 0.0)
    desired = max(_num(desired_size), 0.0)
    capacity_f = max(_num(capacity), 0.0)
    final_value = min(desired, capital_f, capacity_f)
    if final_value < desired and capacity_f <= min(desired, capital_f):
        limiting = "LIQUIDEZ"
    elif final_value < desired and capital_f < desired:
        limiting = "CAPITAL"
    else:
        limiting = "RISCO"
    return {
        "desired_value": round(desired, 2),
        "capacity": round(capacity_f, 2),
        "final_value": round(final_value, 2),
        "limiting_factor": limiting,
    }


def calculate_final_position_size(
    capital: Any,
    risk_pct: float,
    entry_price: Any,
    stop_price: Any,
    volume: Any,
    participation_rate: float = 0.01,
) -> dict:
    """Combina sizing por risco, capital disponível e capacidade por liquidez."""
    capital_f = max(_num(capital), 0.0)
    entry = _num(entry_price)
    if capital_f <= 0 or entry <= 0 or _num(volume) <= 0:
        return {
            "size_by_risk": 0,
            "size_by_capacity": 0,
            "final_size": 0,
            "capital_allocated": 0.0,
            "risk_amount": 0.0,
            "capacity_used_pct": 0.0,
            "limiting_factor": "DADOS_INSUFICIENTES",
        }

    by_risk = estimate_position_size_by_risk(capital_f, risk_pct, entry, stop_price)
    capacity_value = estimate_trade_capacity(volume, participation_rate)
    size_by_capacity = int(capacity_value // entry) if entry > 0 else 0
    final_size = min(int(by_risk["quantity"]), size_by_capacity, int(capital_f // entry))
    allocated = final_size * entry
    if final_size == int(by_risk["quantity"]) and final_size <= size_by_capacity:
        limiting = "RISCO"
    elif final_size == size_by_capacity:
        limiting = "LIQUIDEZ"
    else:
        limiting = "CAPITAL"
    return {
        "size_by_risk": int(by_risk["quantity"]),
        "size_by_capacity": int(size_by_capacity),
        "final_size": int(final_size),
        "capital_allocated": round(allocated, 2),
        "risk_amount": round(final_size * by_risk["risk_per_unit"], 2),
        "capacity_used_pct": round((allocated / capacity_value * 100.0) if capacity_value else 0.0, 4),
        "limiting_factor": limiting,
    }


def classify_capacity(volume: Any, capital: Any, desired_allocation: Any, participation_rate: float = 0.01) -> str:
    """Classifica capacidade de alocação usando volume financeiro disponível."""
    desired = max(_num(desired_allocation), 0.0)
    capital_f = max(_num(capital), 0.0)
    capacity = estimate_trade_capacity(volume, participation_rate)
    if desired <= 0 or capital_f <= 0 or capacity <= 0:
        return "INVIAVEL"
    ratio = capacity / min(desired, capital_f)
    if ratio >= 5:
        return "ALTA_CAPACIDADE"
    if ratio >= 2:
        return "BOA_CAPACIDADE"
    if ratio >= 1:
        return "CAPACIDADE_LIMITADA"
    if ratio >= 0.5:
        return "BAIXA_CAPACIDADE"
    return "INVIAVEL"
