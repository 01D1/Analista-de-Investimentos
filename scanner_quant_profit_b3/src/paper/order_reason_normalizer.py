"""Normalizacao de motivos de ordens simuladas.

Este modulo diagnostica a origem de custo de ordens de paper trading sem
reescrever historico. Quando metadados estao ausentes, a inferencia fica marcada
com menor confianca e campos faltantes.
"""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


ORDER_REASONS = {
    "ENTRY_SIGNAL",
    "EXIT_STOP_LOSS",
    "EXIT_TAKE_PROFIT",
    "EXIT_TRAILING_STOP",
    "EXIT_DAILY_LOSS",
    "EXIT_WEEKLY_LOSS",
    "EXIT_MAX_DRAWDOWN",
    "EXIT_TIME",
    "EXIT_SIGNAL_REVERSAL",
    "EXIT_GOVERNANCE",
    "EXIT_SIMULATION_END",
    "REBALANCE_RISK",
    "REBALANCE_REGIME",
    "REBALANCE_WEIGHT",
    "REDUCE_POSITION",
    "CLOSE_POSITION",
    "UNKNOWN",
}


def _parse_metadata(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if value is None or pd.isna(value):
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def _missing_fields(row: pd.Series | dict, metadata: dict) -> list[str]:
    missing = []
    for field in ["signal_source", "side", "metadata_json"]:
        value = row.get(field)
        if value is None or pd.isna(value) or str(value).strip() == "":
            missing.append(field)
    side = _clean(row.get("side"))
    if side in {"CLOSE", "SELL"} and not any(metadata.get(k) for k in ["exit_rule_triggered", "exit_reason", "is_simulation_end_close"]):
        missing.append("exit_rule_triggered")
    if _clean(row.get("signal_source")) == "REBALANCE" and not metadata.get("rebalance_event_id"):
        missing.append("rebalance_event_id")
    if not metadata.get("parent_signal_id") and side in {"BUY", "ENTRY"}:
        missing.append("parent_signal_id")
    if not metadata.get("lifecycle_id"):
        missing.append("lifecycle_id")
    return sorted(set(missing))


def _exit_reason_from_text(text: str) -> tuple[str | None, str]:
    upper = _clean(text)
    if not upper:
        return None, ""
    if "STOP_LOSS" in upper or "STOP LOSS" in upper or "ATR_STOP" in upper:
        return "EXIT_STOP_LOSS", "exit_rule_triggered"
    if "TAKE_PROFIT" in upper or "TAKE PROFIT" in upper:
        return "EXIT_TAKE_PROFIT", "exit_rule_triggered"
    if "TRAILING" in upper:
        return "EXIT_TRAILING_STOP", "exit_rule_triggered"
    if "WEEKLY" in upper or "SEMAN" in upper:
        return "EXIT_WEEKLY_LOSS", "exit_rule_triggered"
    if "DAILY" in upper or "DIARI" in upper or "PERDA" in upper:
        return "EXIT_DAILY_LOSS", "exit_rule_triggered"
    if "MAX_DRAWDOWN" in upper or "DRAWDOWN" in upper:
        return "EXIT_MAX_DRAWDOWN", "exit_rule_triggered"
    if "TIME" in upper or "HOLDING" in upper or "FIXED" in upper or "TEMPO" in upper:
        return "EXIT_TIME", "exit_rule_triggered"
    if "REVERS" in upper:
        return "EXIT_SIGNAL_REVERSAL", "exit_rule_triggered"
    if "GOVERN" in upper or "BLOQUE" in upper or "BLOCK" in upper:
        return "EXIT_GOVERNANCE", "exit_rule_triggered"
    if "SIMULATION_END" in upper or "FIM" in upper:
        return "EXIT_SIMULATION_END", "exit_rule_triggered"
    return None, ""


def _result(reason: str, confidence: float, source: str, missing: list[str], metadata: dict) -> dict:
    reason = reason if reason in ORDER_REASONS else "UNKNOWN"
    return {
        "normalized_order_reason": reason,
        "reason_confidence": float(confidence),
        "reason_source": source,
        "missing_metadata_fields": missing,
        "metadata_json": json.dumps(metadata, ensure_ascii=False, default=str),
    }


def normalize_order_reason(order_row) -> dict:
    """Inferir motivo normalizado de uma ordem simulada.

    Retorna diagnostico com motivo, confianca, origem da inferencia e campos de
    metadata ausentes. A funcao nao altera dados persistidos.
    """
    row = order_row.to_dict() if hasattr(order_row, "to_dict") else dict(order_row)
    metadata = _parse_metadata(row.get("metadata_json"))
    missing = _missing_fields(row, metadata)
    existing = _clean(row.get("normalized_order_reason") or metadata.get("normalized_order_reason"))
    if existing in ORDER_REASONS and existing != "UNKNOWN":
        return _result(existing, 0.98, "normalized_order_reason", missing, metadata)

    signal_source = _clean(row.get("signal_source") or metadata.get("signal_source"))
    side = _clean(row.get("side"))
    order_status = _clean(row.get("order_status") or row.get("status"))
    cost_bucket = _clean(row.get("cost_bucket") or metadata.get("cost_bucket"))

    if bool(metadata.get("is_simulation_end_close")) or signal_source == "SIMULATION_END" or cost_bucket == "SIMULATION_END":
        return _result("EXIT_SIMULATION_END", 0.95, "simulation_end_metadata", missing, metadata)

    for field in ["exit_rule_triggered", "exit_reason", "rejection_reason"]:
        reason, source = _exit_reason_from_text(metadata.get(field) or row.get(field) or "")
        if reason:
            return _result(reason, 0.9 if field != "rejection_reason" else 0.7, source or field, missing, metadata)

    if signal_source == "REBALANCE" or metadata.get("rebalance_event_id") or cost_bucket == "REBALANCE":
        text = _clean(metadata.get("rebalance_reason") or metadata.get("reason") or row.get("reason"))
        if "REGIME" in text:
            return _result("REBALANCE_REGIME", 0.85, "rebalance_metadata", missing, metadata)
        if "WEIGHT" in text or "PESO" in text:
            return _result("REBALANCE_WEIGHT", 0.85, "rebalance_metadata", missing, metadata)
        return _result("REBALANCE_RISK", 0.8, "signal_source", missing, metadata)

    if order_status in {"BLOCKED_GOVERNANCE"}:
        return _result("EXIT_GOVERNANCE", 0.7, "order_status", missing, metadata)

    if side in {"BUY", "ENTRY"}:
        return _result("ENTRY_SIGNAL", 0.85 if signal_source else 0.65, "side", missing, metadata)
    if side in {"REDUCE", "PARTIAL"}:
        return _result("REDUCE_POSITION", 0.75, "side", missing, metadata)
    if side in {"CLOSE", "SELL"}:
        return _result("CLOSE_POSITION", 0.55, "side_without_exit_metadata", missing, metadata)

    return _result("UNKNOWN", 0.0, "metadata_insufficient", missing, metadata)


def normalize_orders_reasons(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Adicionar colunas de diagnostico de motivo as ordens."""
    if orders_df is None or orders_df.empty:
        return pd.DataFrame(
            columns=[
                "normalized_order_reason",
                "reason_confidence",
                "reason_source",
                "is_unknown",
                "missing_metadata_fields",
                "missing_metadata_fields_json",
            ]
        )
    rows = []
    for _, row in orders_df.iterrows():
        diag = normalize_order_reason(row)
        item = row.to_dict()
        item.update(diag)
        item["is_unknown"] = diag["normalized_order_reason"] == "UNKNOWN"
        item["missing_metadata_fields_json"] = json.dumps(diag["missing_metadata_fields"], ensure_ascii=False)
        rows.append(item)
    return pd.DataFrame(rows)
