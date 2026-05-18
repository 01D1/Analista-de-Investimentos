"""Comparação histórica dos snapshots de inteligência integrada."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.integration.asset_intelligence_change_explanations import explain_asset_change


COMPARE_FIELDS = [
    "integrated_score",
    "integrated_status",
    "integrated_governance_status",
    "integrated_confidence",
    "data_quality_score",
    "technical_score_final",
    "technical_status",
    "technical_governance_status",
    "quant_score",
    "quant_signal_type",
    "quant_governance_status",
    "valuation_available",
    "fair_value",
    "upside_pct",
    "valuation_confidence",
    "event_context_type",
    "event_type",
    "event_impact_score",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "option_available",
    "best_option_structure_type",
    "option_structure_score",
    "option_oos_governance_status",
]

TECHNICAL_FIELDS = {"technical_score_final", "technical_status", "technical_governance_status"}
QUANT_FIELDS = {"quant_score", "quant_signal_type", "quant_governance_status"}
VALUATION_FIELDS = {"valuation_available", "fair_value", "upside_pct", "valuation_confidence"}
EVENT_FIELDS = {"event_context_type", "event_type", "event_impact_score"}
REGIME_FIELDS = {"primary_regime", "trend_regime", "volatility_regime", "liquidity_regime"}
OPTIONS_FIELDS = {"option_available", "best_option_structure_type", "option_structure_score", "option_oos_governance_status"}


def _is_missing(value: Any) -> bool:
    return value is None or pd.isna(value)


def _normal(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _num(row, field: str, default: float = 0.0) -> float:
    value = pd.to_numeric(pd.Series([row.get(field, default)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else default


def _changed(prev: Any, curr: Any, field: str) -> bool:
    p = pd.to_numeric(pd.Series([prev]), errors="coerce").iloc[0]
    c = pd.to_numeric(pd.Series([curr]), errors="coerce").iloc[0]
    if pd.notna(p) and pd.notna(c):
        return abs(float(c) - float(p)) > 1e-9
    return _normal(prev) != _normal(curr)


def _material_type(row: dict) -> str:
    if row["status_changed"]:
        return "STATUS_CHANGE"
    if row["governance_changed"]:
        return "GOVERNANCE_CHANGE"
    if abs(float(row["score_delta"] or 0)) >= 10:
        return "SCORE_CHANGE"
    if row["valuation_changed"]:
        return "VALUATION_CHANGE"
    if row["technical_changed"]:
        return "TECHNICAL_CHANGE"
    if row["quant_changed"]:
        return "QUANT_CHANGE"
    if row["event_changed"]:
        return "EVENT_CHANGE"
    if row["regime_changed"]:
        return "REGIME_CHANGE"
    if row["options_changed"]:
        return "OPTIONS_CHANGE"
    if abs(float(row["data_quality_delta"] or 0)) >= 20:
        return "DATA_QUALITY_CHANGE"
    return "NO_MATERIAL_CHANGE"


def compare_asset_snapshots(previous_row, current_row) -> dict:
    prev = previous_row.to_dict() if hasattr(previous_row, "to_dict") else dict(previous_row)
    curr = current_row.to_dict() if hasattr(current_row, "to_dict") else dict(current_row)
    changes: dict[str, dict[str, Any]] = {}
    changed_fields: list[str] = []
    for field in COMPARE_FIELDS:
        if _changed(prev.get(field), curr.get(field), field):
            changed_fields.append(field)
            changes[field] = {"previous": _normal(prev.get(field)), "current": _normal(curr.get(field))}
    row = {
        "ticker": curr.get("ticker") or prev.get("ticker"),
        "previous_snapshot_id": prev.get("id"),
        "current_snapshot_id": curr.get("id"),
        "previous_created_at": prev.get("created_at"),
        "current_created_at": curr.get("created_at"),
        "changed_fields": changed_fields,
        "changes_count": len(changed_fields),
        "score_delta": round(_num(curr, "integrated_score") - _num(prev, "integrated_score"), 4),
        "data_quality_delta": round(_num(curr, "data_quality_score") - _num(prev, "data_quality_score"), 4),
        "status_changed": "integrated_status" in changed_fields,
        "governance_changed": "integrated_governance_status" in changed_fields,
        "valuation_changed": bool(VALUATION_FIELDS.intersection(changed_fields)),
        "technical_changed": bool(TECHNICAL_FIELDS.intersection(changed_fields)),
        "quant_changed": bool(QUANT_FIELDS.intersection(changed_fields)),
        "event_changed": bool(EVENT_FIELDS.intersection(changed_fields)),
        "regime_changed": bool(REGIME_FIELDS.intersection(changed_fields)),
        "options_changed": bool(OPTIONS_FIELDS.intersection(changed_fields)),
    }
    row["material_change_type"] = _material_type(row)
    row["material_change"] = row["material_change_type"] != "NO_MATERIAL_CHANGE"
    row["metadata_json"] = json.dumps(
        {
            "field_changes": changes,
            "previous_status": _normal(prev.get("integrated_status")),
            "current_status": _normal(curr.get("integrated_status")),
            "previous_governance": _normal(prev.get("integrated_governance_status")),
            "current_governance": _normal(curr.get("integrated_governance_status")),
        },
        ensure_ascii=False,
        default=str,
    )
    row["explanation"] = explain_asset_change(row)
    return row


def compare_latest_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ticker",
        "previous_snapshot_id",
        "current_snapshot_id",
        "previous_created_at",
        "current_created_at",
        "changed_fields",
        "changes_count",
        "score_delta",
        "data_quality_delta",
        "status_changed",
        "governance_changed",
        "valuation_changed",
        "technical_changed",
        "quant_changed",
        "event_changed",
        "regime_changed",
        "options_changed",
        "material_change",
        "material_change_type",
        "explanation",
        "metadata_json",
    ]
    if df is None or df.empty or "ticker" not in df.columns:
        return pd.DataFrame(columns=columns)
    rows = []
    work = df.copy()
    work["created_at_sort"] = pd.to_datetime(work.get("created_at"), errors="coerce")
    if "id" not in work.columns:
        work["id"] = range(1, len(work) + 1)
    for _, group in work.sort_values(["ticker", "created_at_sort", "id"], na_position="first").groupby("ticker", dropna=False):
        if len(group) < 2:
            continue
        previous = group.iloc[-2]
        current = group.iloc[-1]
        rows.append(compare_asset_snapshots(previous, current))
    return pd.DataFrame(rows, columns=columns)


def detect_material_changes(diff_df: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    if diff_df is None or diff_df.empty:
        return diff_df if diff_df is not None else pd.DataFrame()
    thresholds = thresholds or {}
    score_threshold = float(thresholds.get("score_delta", 10))
    quality_threshold = float(thresholds.get("data_quality_delta", 20))
    out = diff_df.copy()
    material = (
        out["status_changed"].fillna(False).astype(bool)
        | out["governance_changed"].fillna(False).astype(bool)
        | (pd.to_numeric(out["score_delta"], errors="coerce").abs() >= score_threshold)
        | (pd.to_numeric(out["data_quality_delta"], errors="coerce").abs() >= quality_threshold)
        | out["valuation_changed"].fillna(False).astype(bool)
        | out["event_changed"].fillna(False).astype(bool)
        | out["regime_changed"].fillna(False).astype(bool)
        | out["options_changed"].fillna(False).astype(bool)
    )
    out["material_change"] = material
    out.loc[~material, "material_change_type"] = "NO_MATERIAL_CHANGE"
    return out
