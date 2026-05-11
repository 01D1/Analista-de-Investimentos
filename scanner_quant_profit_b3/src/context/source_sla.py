"""SLA histórico das fontes de dados de eventos."""
from __future__ import annotations

from typing import Any

import pandas as pd


SOURCE_SLA_COLUMNS = [
    "source_name",
    "total_checks",
    "ok_count",
    "warning_count",
    "error_count",
    "missing_count",
    "stale_count",
    "empty_count",
    "availability_pct",
    "ok_pct",
    "warning_pct",
    "error_pct",
    "missing_pct",
    "stale_pct",
    "avg_age_days",
    "max_age_days",
    "latest_status",
    "latest_date",
    "last_ok_at",
    "days_since_last_ok",
    "reliability_class",
]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=SOURCE_SLA_COLUMNS)


def _pct(count: int, total: int) -> float:
    return round((count / total) * 100, 4) if total else 0.0


def _reference_time(df: pd.DataFrame) -> pd.Timestamp:
    checked = pd.to_datetime(df.get("checked_at"), errors="coerce")
    if checked.notna().any():
        return checked.max()
    return pd.Timestamp.now()


def _classify_reliability(availability: float, error_pct: float, stale_pct: float, missing_pct: float, total: int) -> str:
    if total <= 0:
        return "SEM_DADOS"
    if availability < 50 or missing_pct >= 50 or error_pct >= 30:
        return "CRITICA"
    if availability >= 95 and error_pct <= 2 and stale_pct <= 5:
        return "EXCELENTE"
    if availability >= 85 and error_pct <= 5:
        return "BOA"
    if availability >= 70 and error_pct <= 15:
        return "INSTAVEL"
    if availability >= 50:
        return "RUIM"
    return "CRITICA"


def calculate_source_sla(health_history_df: pd.DataFrame, window_days: int = 30) -> pd.DataFrame:
    """Calcula SLA por fonte a partir de `source_health_checks`."""
    if health_history_df is None or health_history_df.empty:
        return _empty()
    df = health_history_df.copy()
    if "source_name" not in df.columns:
        return _empty()
    df["checked_at_dt"] = pd.to_datetime(df.get("checked_at"), errors="coerce")
    reference = _reference_time(df)
    if window_days and df["checked_at_dt"].notna().any():
        cutoff = reference - pd.Timedelta(days=int(window_days))
        df = df[df["checked_at_dt"].isna() | (df["checked_at_dt"] >= cutoff)].copy()
    if df.empty:
        return _empty()

    rows = []
    for source, group in df.groupby("source_name", dropna=False):
        work = group.sort_values("checked_at_dt")
        total = int(len(work))
        status = work.get("status", pd.Series(dtype=str)).fillna("UNKNOWN").astype(str).str.upper()
        counts = status.value_counts().to_dict()
        available = pd.to_numeric(work.get("available"), errors="coerce")
        if available.notna().any():
            availability = round(float(available.fillna(0).mean() * 100), 4)
        else:
            availability = _pct(total - counts.get("MISSING", 0) - counts.get("ERROR", 0), total)
        ages = pd.to_numeric(work.get("age_days"), errors="coerce")
        latest = work.iloc[-1]
        ok_rows = work[status.eq("OK")]
        last_ok_at = ok_rows["checked_at_dt"].max() if not ok_rows.empty else pd.NaT
        days_since_last_ok = (
            float((reference.normalize() - last_ok_at.normalize()).days)
            if pd.notna(last_ok_at)
            else None
        )
        error_pct = _pct(counts.get("ERROR", 0), total)
        missing_pct = _pct(counts.get("MISSING", 0), total)
        stale_pct = _pct(counts.get("STALE", 0), total)
        rows.append(
            {
                "source_name": source,
                "total_checks": total,
                "ok_count": int(counts.get("OK", 0)),
                "warning_count": int(counts.get("WARNING", 0)),
                "error_count": int(counts.get("ERROR", 0)),
                "missing_count": int(counts.get("MISSING", 0)),
                "stale_count": int(counts.get("STALE", 0)),
                "empty_count": int(counts.get("EMPTY", 0)),
                "availability_pct": availability,
                "ok_pct": _pct(counts.get("OK", 0), total),
                "warning_pct": _pct(counts.get("WARNING", 0), total),
                "error_pct": error_pct,
                "missing_pct": missing_pct,
                "stale_pct": stale_pct,
                "avg_age_days": round(float(ages.mean()), 4) if ages.notna().any() else 0.0,
                "max_age_days": round(float(ages.max()), 4) if ages.notna().any() else 0.0,
                "latest_status": latest.get("status"),
                "latest_date": latest.get("latest_date"),
                "last_ok_at": last_ok_at.isoformat() if pd.notna(last_ok_at) else "",
                "days_since_last_ok": days_since_last_ok,
                "reliability_class": _classify_reliability(availability, error_pct, stale_pct, missing_pct, total),
            }
        )
    return pd.DataFrame(rows, columns=SOURCE_SLA_COLUMNS).sort_values("source_name").reset_index(drop=True)


def calculate_overall_sla(source_sla_df: pd.DataFrame) -> dict[str, Any]:
    if source_sla_df is None or source_sla_df.empty:
        return {
            "total_sources": 0,
            "excellent_count": 0,
            "good_count": 0,
            "unstable_count": 0,
            "bad_count": 0,
            "critical_count": 0,
            "overall_availability_pct": 0.0,
            "overall_status": "NO_DATA",
            "worst_sources": [],
            "best_sources": [],
        }
    df = source_sla_df.copy()
    classes = df.get("reliability_class", pd.Series(dtype=str)).fillna("SEM_DADOS").astype(str).str.upper()
    availability = pd.to_numeric(df.get("availability_pct"), errors="coerce").fillna(0)
    rank = {"EXCELENTE": 0, "BOA": 1, "INSTAVEL": 2, "RUIM": 3, "CRITICA": 4, "SEM_DADOS": 5}
    work = df.assign(_rank=classes.map(rank).fillna(5), _availability=availability)
    if (classes == "CRITICA").any():
        status = "CRITICAL"
    elif classes.isin(["INSTAVEL", "RUIM", "SEM_DADOS"]).any():
        status = "WARNING"
    else:
        status = "OK"
    return {
        "total_sources": int(len(df)),
        "excellent_count": int((classes == "EXCELENTE").sum()),
        "good_count": int((classes == "BOA").sum()),
        "unstable_count": int((classes == "INSTAVEL").sum()),
        "bad_count": int((classes == "RUIM").sum()),
        "critical_count": int((classes == "CRITICA").sum()),
        "overall_availability_pct": round(float(availability.mean()), 4) if len(df) else 0.0,
        "overall_status": status,
        "worst_sources": work.sort_values(["_rank", "_availability"], ascending=[False, True])["source_name"].head(3).astype(str).tolist(),
        "best_sources": work.sort_values(["_rank", "_availability"], ascending=[True, False])["source_name"].head(3).astype(str).tolist(),
    }
