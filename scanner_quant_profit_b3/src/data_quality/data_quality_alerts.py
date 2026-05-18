"""Alertas derivados da auditoria de qualidade das fontes."""
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


def build_alerts_from_data_source_audit(audit_df: pd.DataFrame) -> pd.DataFrame:
    if audit_df is None or audit_df.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)
    alerts: list[dict] = []
    for _, row in audit_df.iterrows():
        source = str(row.get("source_name") or "data_source")
        status = str(row.get("status") or "").upper()
        reliability = str(row.get("reliability_class") or "").upper()
        score = float(row.get("reliability_score") or 0)
        stype = str(row.get("source_type") or "").upper()
        origin = str(row.get("primary_or_secondary") or "").upper()
        meta = row.to_dict()
        if status == "MISSING":
            alerts.append(_alert("DATA_SOURCE_MISSING", "CRITICAL" if origin == "PRIMARY" else "WARNING", "Fonte de dados ausente", row.get("message", ""), source, meta))
        if status == "STALE":
            alert_type = "PROFIT_RTD_STALE" if source == "profit_rtd" else ("B3_DATA_STALE" if source == "b3_cotahist" else ("CVM_DATA_STALE" if source == "cvm_ipe" else "DATA_SOURCE_STALE"))
            alerts.append(_alert(alert_type, "WARNING", "Fonte de dados desatualizada", row.get("message", ""), source, meta))
        if reliability in {"FRAGIL", "INSUFICIENTE", "INDISPONIVEL"} or score < 40:
            alerts.append(_alert("DATA_SOURCE_LOW_RELIABILITY", "WARNING", "Confiabilidade baixa da fonte", f"{source}: score {score:.1f} ({reliability}).", source, meta))
        if origin == "PRIMARY" and status in {"MISSING", "ERROR"}:
            alerts.append(_alert("PRIMARY_SOURCE_UNAVAILABLE", "CRITICAL", "Fonte primaria indisponivel", row.get("message", ""), source, meta))
        if not str(row.get("expected_path_or_url") or "").strip():
            alerts.append(_alert("TRACEABILITY_MISSING", "WARNING", "Rastreabilidade incompleta", f"{source} sem caminho ou URL de origem.", source, meta))
        if source == "options_chain" and str(row.get("message", "")).upper().find("SEM_DADOS") >= 0:
            alerts.append(_alert("OPTIONS_DATA_INSUFFICIENT", "WARNING", "Dados de opcoes insuficientes", row.get("message", ""), source, meta))
        if source == "valuation_pipeline" and status in {"STALE", "WARNING"}:
            alerts.append(_alert("VALUATION_STALE", "WARNING", "Valuation possivelmente desatualizado", row.get("message", ""), source, meta))
        if stype == "COMPANY_IR" and status in {"MISSING", "MISSING_URL"}:
            alerts.append(_alert("RI_URL_MISSING", "INFO", "URL de RI ausente", row.get("message", ""), source, meta))
    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)

