"""Observabilidade histórica da rotina diária."""
from __future__ import annotations

from typing import Any

import pandas as pd


def _window(df: pd.DataFrame, window_days: int) -> pd.DataFrame:
    if df is None or df.empty or "started_at" not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    out["started_at_dt"] = pd.to_datetime(out["started_at"], errors="coerce")
    reference = out["started_at_dt"].max() if out["started_at_dt"].notna().any() else pd.Timestamp.now()
    cutoff = reference - pd.Timedelta(days=int(window_days))
    return out[out["started_at_dt"].isna() | (out["started_at_dt"] >= cutoff)].copy()


def summarize_daily_routine_runs(runs_df: pd.DataFrame, window_days: int = 30) -> dict[str, Any]:
    df = _window(runs_df, window_days)
    if df.empty:
        return {
            "total_runs": 0,
            "success_count": 0,
            "success_with_warnings_count": 0,
            "failed_count": 0,
            "dry_run_count": 0,
            "success_rate_pct": 0.0,
            "warning_rate_pct": 0.0,
            "failure_rate_pct": 0.0,
            "avg_events_loaded": 0.0,
            "avg_signals_covered_pct": 0.0,
            "avg_alerts_count": 0.0,
            "latest_run_status": "",
            "latest_run_at": "",
            "days_since_last_run": None,
            "routine_health_status": "NO_RUNS",
        }
    df = df.sort_values("started_at_dt")
    status = df.get("status", pd.Series(dtype=str)).fillna("").astype(str).str.upper()
    total = int(len(df))
    success = int((status == "SUCCESS").sum())
    warn = int((status == "SUCCESS_WITH_WARNINGS").sum())
    failed = int((status == "FAILED").sum())
    dry = int((status == "DRY_RUN").sum())
    latest = df.iloc[-1]
    reference = df["started_at_dt"].max()
    days_since = float((pd.Timestamp.now().normalize() - reference.normalize()).days) if pd.notna(reference) else None
    if failed > 0 or (days_since is not None and days_since > 3):
        health = "CRITICAL"
    elif warn > 0 or (days_since is not None and days_since > 1):
        health = "WARNING"
    else:
        health = "OK"
    events_loaded = pd.to_numeric(df.get("events_loaded"), errors="coerce")
    signals = pd.to_numeric(df.get("signals_covered_pct"), errors="coerce")
    alerts = pd.to_numeric(df.get("alerts_count"), errors="coerce")
    return {
        "total_runs": total,
        "success_count": success,
        "success_with_warnings_count": warn,
        "failed_count": failed,
        "dry_run_count": dry,
        "success_rate_pct": round(((success + warn) / total) * 100, 4),
        "warning_rate_pct": round((warn / total) * 100, 4),
        "failure_rate_pct": round((failed / total) * 100, 4),
        "avg_events_loaded": round(float(events_loaded.mean()), 4) if events_loaded.notna().any() else 0.0,
        "avg_signals_covered_pct": round(float(signals.mean()), 6) if signals.notna().any() else 0.0,
        "avg_alerts_count": round(float(alerts.mean()), 4) if alerts.notna().any() else 0.0,
        "latest_run_status": latest.get("status"),
        "latest_run_at": latest.get("started_at"),
        "days_since_last_run": days_since,
        "routine_health_status": health,
    }


def generate_routine_observability_report(summary: dict[str, Any]) -> str:
    total = int((summary or {}).get("total_runs") or 0)
    if total == 0:
        return "A rotina diária ainda não possui execuções registradas na janela analisada."
    return (
        f"A rotina diária executou {total} vezes na janela, com taxa de sucesso de "
        f"{float(summary.get('success_rate_pct') or 0):.1f}%. "
        f"O último status foi {summary.get('latest_run_status') or 'indefinido'}, "
        f"com média de {float(summary.get('avg_alerts_count') or 0):.1f} alertas por execução."
    )
