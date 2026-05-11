"""Analytics de alertas operacionais."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _window(df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    if df is None or df.empty or "created_at" not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    out["created_at_dt"] = pd.to_datetime(out["created_at"], errors="coerce")
    reference = out["created_at_dt"].max() if out["created_at_dt"].notna().any() else pd.Timestamp.now()
    cutoff = reference - pd.Timedelta(days=int(window_days))
    return out[out["created_at_dt"].isna() | (out["created_at_dt"] >= cutoff)].copy()


def detect_recurring_alerts(alerts_df: pd.DataFrame, min_occurrences: int = 3) -> pd.DataFrame:
    columns = ["alert_type", "source", "severity", "occurrences"]
    if alerts_df is None or alerts_df.empty:
        return pd.DataFrame(columns=columns)
    df = alerts_df.copy()
    for col in ["alert_type", "source", "severity"]:
        if col not in df.columns:
            df[col] = ""
    grouped = df.groupby(["alert_type", "source", "severity"], dropna=False).size().reset_index(name="occurrences")
    return grouped[grouped["occurrences"] >= int(min_occurrences)].sort_values("occurrences", ascending=False).reset_index(drop=True)


def summarize_alerts(alerts_df: pd.DataFrame, window_days: int = 30) -> dict[str, Any]:
    df = _window(alerts_df, window_days)
    if df.empty:
        return {
            "total_alerts": 0,
            "open_alerts": 0,
            "resolved_alerts": 0,
            "critical_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "alerts_by_type": {},
            "alerts_by_source": {},
            "most_common_alert_type": "",
            "most_problematic_source": "",
            "avg_resolution_time_hours": None,
            "recurring_alerts": [],
        }
    severity = df.get("severity", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    resolved = pd.to_numeric(df.get("resolved"), errors="coerce").fillna(0)
    by_type = df.get("alert_type", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str).value_counts().to_dict()
    by_source = df.get("source", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str).value_counts().to_dict()
    resolved_at = pd.to_datetime(df.get("resolved_at"), errors="coerce")
    created_at = pd.to_datetime(df.get("created_at"), errors="coerce")
    resolution_hours = ((resolved_at - created_at).dt.total_seconds() / 3600).dropna()
    recurring = detect_recurring_alerts(df).to_dict(orient="records")
    return {
        "total_alerts": int(len(df)),
        "open_alerts": int((resolved == 0).sum()),
        "resolved_alerts": int((resolved != 0).sum()),
        "critical_count": int((severity == "CRITICAL").sum()),
        "warning_count": int((severity == "WARNING").sum()),
        "info_count": int((severity == "INFO").sum()),
        "alerts_by_type": by_type,
        "alerts_by_source": by_source,
        "most_common_alert_type": max(by_type, key=by_type.get) if by_type else "",
        "most_problematic_source": max(by_source, key=by_source.get) if by_source else "",
        "avg_resolution_time_hours": round(float(resolution_hours.mean()), 4) if not resolution_hours.empty else None,
        "recurring_alerts": recurring,
    }


def generate_alerts_report(alert_summary: dict[str, Any]) -> str:
    total = int((alert_summary or {}).get("total_alerts") or 0)
    if total == 0:
        return "Nenhum alerta operacional foi registrado na janela analisada."
    critical = int(alert_summary.get("critical_count") or 0)
    source = alert_summary.get("most_problematic_source") or "indefinida"
    alert_type = alert_summary.get("most_common_alert_type") or "indefinido"
    return (
        f"Foram registrados {total} alertas na janela analisada, sendo {critical} críticos. "
        f"A fonte com mais alertas foi {source}, principalmente por {alert_type}. "
        "Revise a rotina da fonte antes de usar ausência de eventos como evidência."
    )
