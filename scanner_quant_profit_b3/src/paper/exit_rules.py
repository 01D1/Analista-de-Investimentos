"""Regras avançadas de saída simulada."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import pandas as pd

from src.paper.stop_engine import (
    calculate_fixed_stop,
    calculate_take_profit,
    check_stop_triggered,
    check_take_profit_triggered,
    update_trailing_stop,
)


@dataclass
class ExitRule:
    rule_id: str
    rule_type: str
    enabled: bool = True
    priority: int = 100
    parameters_json: str = "{}"
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_PRIORITIES = {
    "GOVERNANCE_EXIT": 1,
    "DAILY_LOSS_EXIT": 2,
    "WEEKLY_LOSS_EXIT": 2,
    "VAR_STOP": 3,
    "STOP_LOSS_PCT": 4,
    "ATR_STOP": 4,
    "TRAILING_STOP": 4,
    "SIGNAL_REVERSAL_EXIT": 5,
    "TAKE_PROFIT_PCT": 6,
    "TIME_EXIT": 7,
    "FIXED_HOLDING_DAYS": 8,
}


def _params(rule) -> dict:
    raw = rule.parameters_json if hasattr(rule, "parameters_json") else rule.get("parameters_json", "{}")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _rule_type(rule) -> str:
    return str(rule.rule_type if hasattr(rule, "rule_type") else rule.get("rule_type", "")).upper()


def _enabled(rule) -> bool:
    return bool(rule.enabled if hasattr(rule, "enabled") else rule.get("enabled", True))


def _position_value(position, key, default=None):
    if hasattr(position, key):
        return getattr(position, key)
    if hasattr(position, "get"):
        return position.get(key, default)
    return default


def _num(value, default=0.0):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def _result(triggered=False, reason="NO_EXIT", rule_type=None, price=None, metadata=None):
    return {
        "should_exit": bool(triggered),
        "exit_reason": reason,
        "exit_rule_triggered": rule_type,
        "exit_price_hint": price,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
    }


def evaluate_exit_rules(position, market_row, risk_row=None, regime_row=None, signal_row=None, rules=None) -> dict:
    rules = rules or []
    if not rules:
        return _result()
    ordered = sorted([r for r in rules if _enabled(r)], key=lambda r: getattr(r, "priority", None) or DEFAULT_PRIORITIES.get(_rule_type(r), 99))
    entry = _num(_position_value(position, "avg_price"))
    current = _num(market_row.get("close"), entry)
    low = market_row.get("low", current)
    high = market_row.get("high", current)
    hold_days = int(_num(_position_value(position, "holding_days", 0), 0))
    metadata = {}

    for rule in ordered:
        rule_type = _rule_type(rule)
        params = _params(rule)
        if rule_type == "GOVERNANCE_EXIT":
            values = " ".join(str((signal_row or {}).get(c, "")) for c in ["integrated_governance_status", "governance_status", "risk_status"])
            if "BLOCKED" in values.upper() or "BLOQUEADO" in values.upper():
                return _result(True, "Saída simulada por governança.", rule_type, current, params)
        elif rule_type == "VAR_STOP" and risk_row is not None and hasattr(risk_row, "get"):
            if "BLOCKED" in str(risk_row.get("risk_status", "")).upper():
                return _result(True, "Saída simulada por VaR/risco.", rule_type, current, params)
        elif rule_type == "STOP_LOSS_PCT":
            stop = calculate_fixed_stop(entry, params.get("stop_loss_pct", 0.03))
            check = check_stop_triggered(low, high, stop)
            if check["triggered"]:
                return _result(True, "Stop loss simulado acionado.", rule_type, check["execution_price"], {"stop": stop})
        elif rule_type == "ATR_STOP":
            atr = params.get("atr")
            stop = entry - float(atr or 0) * float(params.get("atr_multiplier", 2)) if atr else None
            check = check_stop_triggered(low, high, stop)
            if check["triggered"]:
                return _result(True, "ATR stop simulado acionado.", rule_type, check["execution_price"], {"stop": stop})
        elif rule_type == "TRAILING_STOP":
            previous = _position_value(position, "trailing_stop", None)
            trailing = update_trailing_stop(previous, current, params.get("trailing_stop_pct", 0.04))
            metadata["trailing_stop"] = trailing
            check = check_stop_triggered(low, high, trailing)
            if check["triggered"]:
                return _result(True, "Trailing stop simulado acionado.", rule_type, check["execution_price"], metadata)
        elif rule_type == "SIGNAL_REVERSAL_EXIT" and signal_row is not None:
            values = " ".join(str(signal_row.get(c, "")) for c in ["signal_type", "setup_direction", "integrated_status"])
            if any(token in values.upper() for token in ["VENDA", "BEARISH", "DIVERGENCIA", "FRACO"]):
                return _result(True, "Reversão de sinal simulada.", rule_type, current, params)
        elif rule_type == "TAKE_PROFIT_PCT":
            target = calculate_take_profit(entry, params.get("take_profit_pct", 0.06))
            check = check_take_profit_triggered(low, high, target)
            if check["triggered"]:
                return _result(True, "Take-profit simulado acionado.", rule_type, check["execution_price"], {"target": target})
        elif rule_type in {"TIME_EXIT", "FIXED_HOLDING_DAYS"}:
            max_days = int(params.get("holding_days", params.get("max_holding_days", 5)))
            if hold_days >= max_days:
                return _result(True, "Saída simulada por tempo.", rule_type, current, {"holding_days": hold_days})
        elif rule_type == "REGIME_EXIT" and regime_row is not None:
            regime_text = " ".join(str(regime_row.get(c, "")) for c in ["primary_regime", "trend_regime", "volatility_regime", "risk_regime"])
            if any(token in regime_text.upper() for token in ["BAIXA_TENDENCIAL", "RISCO_ELEVADO", "LIQUIDEZ_FRACA"]):
                return _result(True, "Saída simulada por regime.", rule_type, current, params)
    return _result(False, "Sem regra de saída simulada acionada.", None, None, metadata)

