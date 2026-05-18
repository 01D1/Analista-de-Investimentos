"""Explicações analíticas para mudanças entre snapshots integrados."""
from __future__ import annotations

import json

import pandas as pd


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def _metadata(diff_row) -> dict:
    raw = diff_row.get("metadata_json", "{}") if hasattr(diff_row, "get") else "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _change(meta: dict, field: str) -> tuple:
    data = meta.get("field_changes", {}).get(field, {})
    return data.get("previous"), data.get("current")


def explain_score_change(diff_row) -> str:
    delta = _num(diff_row.get("score_delta"))
    if abs(delta) < 1e-9:
        return "O score integrado permaneceu estável."
    direction = "subiu" if delta > 0 else "caiu"
    return f"O score integrado {direction} {abs(delta):.2f} pontos."


def explain_governance_change(diff_row) -> str:
    if not bool(diff_row.get("governance_changed")):
        return "A governança integrada não mudou."
    prev, curr = _change(_metadata(diff_row), "integrated_governance_status")
    return f"A governança integrada mudou de {prev or '-'} para {curr or '-'}."


def explain_valuation_change(diff_row) -> str:
    if not bool(diff_row.get("valuation_changed")):
        return "O bloco de valuation permaneceu sem mudança material."
    meta = _metadata(diff_row)
    prev, curr = _change(meta, "upside_pct")
    if prev is not None or curr is not None:
        return f"O upside mudou de {prev or '-'} para {curr or '-'}."
    return "Houve mudança no bloco de valuation/fundamentos."


def explain_event_change(diff_row) -> str:
    if not bool(diff_row.get("event_changed")):
        return "O contexto de eventos permaneceu estável."
    meta = _metadata(diff_row)
    prev, curr = _change(meta, "event_type")
    if prev is None and curr is None:
        prev, curr = _change(meta, "event_impact_score")
        return f"O impacto do evento mudou de {prev or '-'} para {curr or '-'}."
    return f"O contexto de eventos mudou de {prev or '-'} para {curr or '-'}."


def explain_regime_change(diff_row) -> str:
    if not bool(diff_row.get("regime_changed")):
        return "O regime de mercado permaneceu estável."
    prev, curr = _change(_metadata(diff_row), "primary_regime")
    return f"O regime principal mudou de {prev or '-'} para {curr or '-'}."


def explain_options_change(diff_row) -> str:
    if not bool(diff_row.get("options_changed")):
        return "O bloco de opções permaneceu sem mudança material."
    prev, curr = _change(_metadata(diff_row), "best_option_structure_type")
    return f"O componente de opções mudou de {prev or '-'} para {curr or '-'}."


def explain_data_quality_change(diff_row) -> str:
    delta = _num(diff_row.get("data_quality_delta"))
    if abs(delta) < 1e-9:
        return "A qualidade de dados permaneceu estável."
    direction = "melhorou" if delta > 0 else "piorou"
    return f"A qualidade de dados {direction} {abs(delta):.2f} pontos."


def explain_asset_change(diff_row) -> str:
    ticker = diff_row.get("ticker", "ativo")
    meta = _metadata(diff_row)
    prev_status, curr_status = _change(meta, "integrated_status")
    prev_status = prev_status or meta.get("previous_status")
    curr_status = curr_status or meta.get("current_status")
    parts = []
    if bool(diff_row.get("status_changed")):
        parts.append(f"{ticker} mudou de {prev_status or '-'} para {curr_status or '-'}.")
    else:
        parts.append(f"{ticker} manteve status {curr_status or prev_status or '-'} no comparativo.")
    if bool(diff_row.get("governance_changed")):
        parts.append(explain_governance_change(diff_row))
    if abs(_num(diff_row.get("score_delta"))) >= 1e-9:
        parts.append(explain_score_change(diff_row))
    if bool(diff_row.get("valuation_changed")):
        parts.append(explain_valuation_change(diff_row))
    if bool(diff_row.get("event_changed")):
        parts.append(explain_event_change(diff_row))
    if bool(diff_row.get("regime_changed")):
        parts.append(explain_regime_change(diff_row))
    if bool(diff_row.get("options_changed")):
        parts.append(explain_options_change(diff_row))
    if bool(diff_row.get("data_quality_delta")):
        parts.append(explain_data_quality_change(diff_row))
    parts.append("Leitura analítica e auditável; não constitui recomendação.")
    return " ".join(parts)
