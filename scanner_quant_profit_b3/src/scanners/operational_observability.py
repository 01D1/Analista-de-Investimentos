"""CLI de SLA e observabilidade operacional."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.context.coverage_trends import (
    calculate_event_coverage_trend,
    calculate_regime_coverage_trend,
    generate_coverage_trend_report,
)
from src.context.observability_store import (
    save_operational_observability_snapshot,
    save_source_sla_snapshot,
)
from src.context.routine_observability import generate_routine_observability_report, summarize_daily_routine_runs
from src.context.source_sla import calculate_overall_sla, calculate_source_sla
from src.notifications.alert_analytics import generate_alerts_report, summarize_alerts
from src.notifications.alert_engine import build_alerts_from_observability
from src.notifications.alert_store import save_alerts
from src.utils import load_config, project_path


def _read_table(db_path: Path, table: str) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table}", con)
    except Exception:
        return pd.DataFrame()


def _write_csvs(outputs: dict[str, Any]) -> dict[str, Path]:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "source_sla": reports_dir / f"source_sla_{stamp}.csv",
        "operational_observability": reports_dir / f"operational_observability_{stamp}.csv",
        "alert_analytics": reports_dir / f"alert_analytics_{stamp}.csv",
        "coverage_trends": reports_dir / f"coverage_trends_{stamp}.csv",
    }
    outputs["source_sla"].to_csv(paths["source_sla"], index=False, sep=";", decimal=",")
    pd.DataFrame([outputs["summary"]]).to_csv(paths["operational_observability"], index=False, sep=";", decimal=",")
    pd.DataFrame([outputs["alert_summary"]]).to_csv(paths["alert_analytics"], index=False, sep=";", decimal=",")
    outputs["coverage_trend"].to_csv(paths["coverage_trends"], index=False, sep=";", decimal=",")
    return paths


def _compose_summary(
    *,
    window_days: int,
    overall_sla: dict[str, Any],
    alert_summary: dict[str, Any],
    routine_summary: dict[str, Any],
    coverage_trend: pd.DataFrame,
    source_sla: pd.DataFrame,
    coverage_report: str,
    alerts_report: str,
    routine_report: str,
) -> dict[str, Any]:
    trend = coverage_trend["coverage_trend_direction"].iloc[-1] if coverage_trend is not None and not coverage_trend.empty else "INSUFICIENTE"
    latest_coverage = float(coverage_trend["avg_signals_with_event_pct"].iloc[-1]) if coverage_trend is not None and not coverage_trend.empty else 0.0
    classes = source_sla.get("reliability_class", pd.Series(dtype=str)).fillna("").astype(str).str.upper() if source_sla is not None and not source_sla.empty else pd.Series(dtype=str)
    critical_sources = source_sla.loc[classes.eq("CRITICA"), "source_name"].astype(str).tolist() if not source_sla.empty else []
    unstable_sources = source_sla.loc[classes.isin(["INSTAVEL", "RUIM"]), "source_name"].astype(str).tolist() if not source_sla.empty else []
    if overall_sla.get("overall_status") == "CRITICAL" or routine_summary.get("routine_health_status") == "CRITICAL":
        status = "CRITICAL"
    elif overall_sla.get("overall_status") in {"WARNING", "NO_DATA"} or alert_summary.get("open_alerts", 0) or trend in {"PIORANDO", "INSUFICIENTE"}:
        status = "WARNING"
    else:
        status = "OK"
    summary_text = (
        f"Overall status: {status}. "
        f"Disponibilidade média: {float(overall_sla.get('overall_availability_pct') or 0):.1f}%. "
        f"Fontes críticas: {len(critical_sources)}. "
        f"Alertas abertos: {int(alert_summary.get('open_alerts') or 0)}. "
        f"Rotina: {routine_summary.get('routine_health_status')}. "
        f"Cobertura média recente: {latest_coverage:.2%}. "
        f"{coverage_report} {alerts_report} {routine_report}"
    )
    return {
        "window_days": int(window_days),
        "overall_status": status,
        "overall_availability_pct": overall_sla.get("overall_availability_pct", 0.0),
        "total_sources": overall_sla.get("total_sources", 0),
        "critical_sources": len(critical_sources),
        "critical_sources_list": critical_sources,
        "unstable_sources_list": unstable_sources,
        "total_alerts": alert_summary.get("total_alerts", 0),
        "critical_alerts": alert_summary.get("critical_count", 0),
        "open_alerts": alert_summary.get("open_alerts", 0),
        "recurring_alerts": alert_summary.get("recurring_alerts", []),
        "routine_success_rate_pct": routine_summary.get("success_rate_pct", 0),
        "routine_failure_rate_pct": routine_summary.get("failure_rate_pct", 0),
        "routine_health_status": routine_summary.get("routine_health_status"),
        "latest_run_at": routine_summary.get("latest_run_at"),
        "avg_signals_covered_pct": latest_coverage,
        "coverage_trend_direction": trend,
        "summary_text": summary_text,
    }


def run(*, window_days: int = 30, save_db: bool = False, write_csv: bool = False, verbose: bool = False, db_path: str | Path | None = None) -> dict[str, Any]:
    cfg = load_config()
    db_path = Path(db_path) if db_path else project_path(cfg["database_path"])
    health_history = _read_table(db_path, "source_health_checks")
    coverage_runs = _read_table(db_path, "event_coverage_runs")
    coverage_by_regime = _read_table(db_path, "event_coverage_by_regime")
    alerts = _read_table(db_path, "operational_alerts")
    routine_runs = _read_table(db_path, "daily_routine_runs")

    source_sla = calculate_source_sla(health_history, window_days=window_days)
    overall_sla = calculate_overall_sla(source_sla)
    coverage_trend = calculate_event_coverage_trend(coverage_runs)
    regime_trend = calculate_regime_coverage_trend(coverage_by_regime)
    alert_summary = summarize_alerts(alerts, window_days=window_days)
    routine_summary = summarize_daily_routine_runs(routine_runs, window_days=window_days)
    coverage_report = generate_coverage_trend_report(coverage_trend, regime_trend)
    alerts_report = generate_alerts_report(alert_summary)
    routine_report = generate_routine_observability_report(routine_summary)
    summary = _compose_summary(
        window_days=window_days,
        overall_sla=overall_sla,
        alert_summary=alert_summary,
        routine_summary=routine_summary,
        coverage_trend=coverage_trend,
        source_sla=source_sla,
        coverage_report=coverage_report,
        alerts_report=alerts_report,
        routine_report=routine_report,
    )
    obs_alerts = build_alerts_from_observability(summary)
    paths = _write_csvs({"source_sla": source_sla, "summary": summary, "alert_summary": alert_summary, "coverage_trend": coverage_trend}) if write_csv else {}
    snapshot_id = None
    sla_rows = 0
    alerts_saved = 0
    if save_db:
        sla_rows = save_source_sla_snapshot(db_path, source_sla, window_days)
        snapshot_id = save_operational_observability_snapshot(db_path, summary)
        alerts_saved = save_alerts(db_path, obs_alerts)

    print("\nOPERATIONAL OBSERVABILITY REPORT")
    print(f"Overall status: {summary['overall_status']}")
    print(f"Overall availability: {float(summary['overall_availability_pct'] or 0):.1f}%")
    print(f"Critical sources: {summary['critical_sources']}")
    print(f"Open alerts: {summary['open_alerts']}")
    print(f"Routine success rate: {float(summary['routine_success_rate_pct'] or 0):.1f}%")
    print(f"Coverage trend: {summary['coverage_trend_direction']}")
    print("\nResumo:")
    print(summary["summary_text"])
    if verbose and not source_sla.empty:
        print("\nSLA por fonte:")
        print(source_sla.to_string(index=False))
    if save_db:
        print(f"\nSnapshots salvos: observability_id={snapshot_id}; sla_rows={sla_rows}; alerts_saved={alerts_saved}")
    if write_csv:
        print("\nCSVs gerados:")
        for name, path in paths.items():
            print(f"- {name}: {path}")
    return {
        "source_sla": source_sla,
        "overall_sla": overall_sla,
        "coverage_trend": coverage_trend,
        "regime_trend": regime_trend,
        "alert_summary": alert_summary,
        "routine_summary": routine_summary,
        "summary": summary,
        "alerts": obs_alerts,
        "snapshot_id": snapshot_id,
        "csv_paths": paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SLA e observabilidade operacional do scanner quantitativo.")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run(window_days=args.window_days, save_db=args.save_db, write_csv=args.write_csv, verbose=args.verbose)


if __name__ == "__main__":
    main()
