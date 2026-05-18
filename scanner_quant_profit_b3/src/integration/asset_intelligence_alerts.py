"""Alertas derivados de mudanças materiais no snapshot integrado."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd


ALERT_COLUMNS = ["alert_type", "severity", "title", "message", "source", "created_at", "metadata_json"]


def _alert(alert_type: str, severity: str, title: str, message: str, source: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "source": source,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "metadata_json": json.dumps(metadata, ensure_ascii=False, default=str),
    }


def build_alerts_from_asset_diffs(diff_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if diff_df is None or diff_df.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)
    for _, row in diff_df.iterrows():
        ticker = str(row.get("ticker") or "")
        status_type = str(row.get("material_change_type") or "")
        score_delta = float(pd.to_numeric(pd.Series([row.get("score_delta")]), errors="coerce").fillna(0).iloc[0])
        quality_delta = float(pd.to_numeric(pd.Series([row.get("data_quality_delta")]), errors="coerce").fillna(0).iloc[0])
        explanation = str(row.get("explanation") or "")
        metadata = row.to_dict()
        if bool(row.get("status_changed")):
            severity = "CRITICAL" if "BLOQUEADO" in explanation.upper() or "BLOCKED" in explanation.upper() else "WARNING"
            rows.append(_alert("ASSET_STATUS_CHANGED", severity, f"{ticker}: status integrado mudou", explanation, ticker, metadata))
        if bool(row.get("governance_changed")):
            alert_type = "ASSET_GOVERNANCE_BLOCKED" if "BLOCKED" in explanation.upper() or "BLOQUEADO" in explanation.upper() else "ASSET_GOVERNANCE_UNBLOCKED"
            rows.append(_alert(alert_type, "WARNING", f"{ticker}: governança integrada mudou", explanation, ticker, metadata))
        if score_delta <= -20:
            rows.append(_alert("ASSET_SCORE_DROPPED", "WARNING", f"{ticker}: score integrado caiu", explanation, ticker, metadata))
        elif score_delta >= 20:
            rows.append(_alert("ASSET_SCORE_IMPROVED", "INFO", f"{ticker}: score integrado melhorou", explanation, ticker, metadata))
        if bool(row.get("valuation_changed")):
            rows.append(_alert("ASSET_VALUATION_CHANGED", "INFO", f"{ticker}: valuation mudou", explanation, ticker, metadata))
        if bool(row.get("event_changed")):
            rows.append(_alert("ASSET_EVENT_RISK_CHANGED", "WARNING", f"{ticker}: contexto de evento mudou", explanation, ticker, metadata))
        if bool(row.get("regime_changed")):
            rows.append(_alert("ASSET_REGIME_CHANGED", "INFO", f"{ticker}: regime mudou", explanation, ticker, metadata))
        if quality_delta <= -20:
            rows.append(_alert("ASSET_DATA_QUALITY_DROPPED", "WARNING", f"{ticker}: qualidade de dados caiu", explanation, ticker, metadata))
        if status_type == "NO_MATERIAL_CHANGE":
            continue
    return pd.DataFrame(rows, columns=ALERT_COLUMNS)
