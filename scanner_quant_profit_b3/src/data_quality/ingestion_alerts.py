"""Alertas derivados do assistente de ingestao."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from src.notifications.alert_engine import ALERT_COLUMNS


def _alert(alert_type: str, severity: str, title: str, message: str, source: str, metadata: dict | None = None) -> dict:
    return {
        "alert_type": alert_type,
        "severity": severity,
        "title": title,
        "message": message,
        "source": source,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def build_alerts_from_ingestion_run(summary: dict, steps_df: pd.DataFrame, validation_df: pd.DataFrame, comparison_df: pd.DataFrame) -> pd.DataFrame:
    alerts = []
    if steps_df is not None and not steps_df.empty:
        for _, row in steps_df.iterrows():
            status = str(row.get("status") or "").upper()
            if status == "FAILED":
                alerts.append(_alert("INGESTION_STEP_FAILED", "CRITICAL", "Etapa de ingestão falhou", row.get("title", ""), row.get("source_domain", "ingestion"), row.to_dict()))
            if status == "MANUAL_REQUIRED":
                alerts.append(_alert("INGESTION_MANUAL_ACTION_REQUIRED", "INFO", "Ação manual necessária", row.get("title", ""), row.get("source_domain", "ingestion"), row.to_dict()))
    if validation_df is not None and not validation_df.empty:
        for _, row in validation_df.iterrows():
            domain = str(row.get("source_domain") or "")
            status = str(row.get("validation_status") or "").upper()
            if domain == "PROFIT_RTD" and status == "STALE":
                alerts.append(_alert("INGESTION_SOURCE_STILL_STALE", "WARNING", "Fonte ainda stale", row.get("message", ""), domain, row.to_dict()))
            if domain == "B3" and status == "FAILED":
                alerts.append(_alert("INGESTION_B3_STILL_UNPROCESSED", "WARNING", "B3 ainda com lacunas", row.get("message", ""), domain, row.to_dict()))
            if domain == "OPTIONS" and status == "FAILED":
                alerts.append(_alert("INGESTION_OPTIONS_STILL_MISSING", "WARNING", "Opções ainda ausentes", row.get("message", ""), domain, row.to_dict()))
    if comparison_df is not None and not comparison_df.empty and not comparison_df["score_delta"].fillna(0).gt(0).any():
        alerts.append(_alert("INGESTION_NO_IMPROVEMENT", "WARNING", "Sem melhora após ingestão", "A comparação antes/depois não mostrou melhora de confiabilidade.", "ingestion", summary))
    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)

