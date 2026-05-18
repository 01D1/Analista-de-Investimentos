"""Alertas derivados da reconciliacao de fontes."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from src.notifications.alert_engine import ALERT_COLUMNS


MAP = {
    "RAW_PRESENT_DB_EMPTY": "B3_DB_EMPTY",
    "DB_MISSING_YEAR": "B3_RAW_NOT_PROCESSED",
    "RAW_NEWER_THAN_DB": "B3_RAW_NOT_PROCESSED",
    "NO_CHAIN_SNAPSHOTS": "OPTIONS_CHAIN_MISSING",
    "NO_HISTORY": "OPTIONS_CHAIN_MISSING",
    "PROFIT_RTD_STALE": "PROFIT_RTD_STALE",
    "RI_URL_MISSING": "RI_URL_MISSING",
    "ERROR": "RECONCILIATION_FAILED",
}


def build_alerts_from_reconciliation(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return pd.DataFrame(columns=ALERT_COLUMNS)
    rows = []
    for _, row in results_df.iterrows():
        issue = str(row.get("issue_type") or "")
        if issue == "OK":
            continue
        alert_type = MAP.get(issue, "RECONCILIATION_FAILED" if str(row.get("status")).upper() == "ERROR" else "")
        if not alert_type:
            continue
        severity = str(row.get("severity") or "WARNING").upper()
        rows.append(
            {
                "alert_type": alert_type,
                "severity": "CRITICAL" if severity == "CRITICAL" else "WARNING",
                "title": "Reconciliação de fonte pendente",
                "message": row.get("description", ""),
                "source": row.get("source_domain", "data_reconciliation"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "metadata_json": json.dumps(row.to_dict(), ensure_ascii=False, default=str),
            }
        )
    return pd.DataFrame(rows, columns=ALERT_COLUMNS)

