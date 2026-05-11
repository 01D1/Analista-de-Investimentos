"""Orquestrador operacional diário do Radar Quant."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.context.source_health_store import summarize_source_health
from src.notifications.alert_engine import (
    build_alerts_from_event_coverage,
    build_alerts_from_health,
    build_alerts_from_governance,
    build_daily_routine_alerts,
)
from src.notifications.alert_store import save_alerts
from src.scanners import event_daily_update, source_health_check
from src.utils import load_config, project_path
from src.db.init_db import init_database


def _write_report(summary: dict[str, Any], health_df: pd.DataFrame, alerts_df: pd.DataFrame) -> Path:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"daily_quant_routine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    lines = [
        "# Daily Quant Routine",
        "",
        f"- Status: {summary.get('status')}",
        f"- Período: {summary.get('start_date')} a {summary.get('end_date')}",
        f"- Health: {summary.get('health_overall_status')}",
        f"- Cobertura de eventos: {summary.get('event_coverage_quality')}",
        f"- Eventos carregados: {summary.get('events_loaded')}",
        f"- Eventos após dedupe: {summary.get('events_after_dedup')}",
        f"- Sinais cobertos: {summary.get('signals_covered_pct'):.2%}",
        f"- Alertas: {summary.get('alerts_count')}",
        "",
        "## Fontes",
        "",
    ]
    for _, row in health_df.iterrows():
        lines.append(f"- {row.get('status')}: {row.get('source_name')} — {row.get('message')}")
    lines.extend(["", "## Alertas", ""])
    if alerts_df.empty:
        lines.append("- Sem alertas.")
    else:
        for _, row in alerts_df.iterrows():
            lines.append(f"- [{row.get('severity')}] {row.get('alert_type')}: {row.get('title')}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _save_routine_run(db_path: Path, summary: dict[str, Any]) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO daily_routine_runs (
                started_at, finished_at, status, start_date, end_date, sources,
                health_overall_status, event_coverage_quality, events_loaded,
                events_after_dedup, signals_covered_pct, governance_status,
                alerts_count, report_path, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.get("started_at"),
                summary.get("finished_at"),
                summary.get("status"),
                summary.get("start_date"),
                summary.get("end_date"),
                ",".join(summary.get("sources") or []),
                summary.get("health_overall_status"),
                summary.get("event_coverage_quality"),
                int(summary.get("events_loaded") or 0),
                int(summary.get("events_after_dedup") or 0),
                float(summary.get("signals_covered_pct") or 0),
                summary.get("governance_status"),
                int(summary.get("alerts_count") or 0),
                str(summary.get("report_path") or ""),
                json.dumps(summary.get("metadata") or {}, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def _concat_alerts(frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = [frame for frame in frames if frame is not None and not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    sources: list[str] | None = None,
    with_regimes: bool = False,
    with_event_context: bool = False,
    with_governance: bool = False,
    save_db: bool = False,
    write_csv: bool = False,
    fail_on_error: bool = False,
    dry_run: bool = False,
    config_path: str | Path = "config/events.yaml",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = datetime.now().isoformat(timespec="seconds")
    cfg = load_config()
    db_path = Path(db_path) if db_path else project_path(cfg["database_path"])
    health_result = source_health_check.run(
        config_path=config_path,
        save_db=save_db and not dry_run,
        write_csv=write_csv,
        fail_on_error=False,
        db_path=db_path,
    )
    health = health_result["health"]
    health_summary = summarize_source_health(health)
    alerts = [build_alerts_from_health(health)]

    event_result: dict[str, Any] = {}
    governance_result: dict[str, Any] = {}
    fatal_health = health_summary["overall_status"] == "ERROR"
    status = "DRY_RUN" if dry_run else "SUCCESS"
    message = ""
    if fail_on_error and fatal_health:
        status = "FAILED"
        message = "Fonte crítica ausente ou com erro no health check."
    else:
        event_result = event_daily_update.run(
            start=start,
            end=end,
            sources=sources,
            save_db=save_db,
            write_csv=write_csv,
            with_regimes=with_regimes,
            dry_run=dry_run,
            db_path=db_path,
            config_path=config_path,
        )
        alerts.append(build_alerts_from_event_coverage(event_result.get("coverage") or {}))
        if with_event_context and not dry_run:
            try:
                from src.scanners import event_context_analysis

                event_context_analysis.run(start=start, end=end, csv=write_csv, save_db=save_db)
            except Exception as exc:
                status = "SUCCESS_WITH_WARNINGS"
                message = f"event_context_analysis falhou: {exc}"
        if with_governance and not dry_run:
            try:
                from src.scanners import governance_review

                governance_result = governance_review.run(source="filter_walk_forward", latest=True, save_db=save_db)
                alerts.append(build_alerts_from_governance(governance_result.get("review")))
            except Exception as exc:
                status = "SUCCESS_WITH_WARNINGS"
                message = f"governance_review falhou: {exc}"

    alerts_df = _concat_alerts(alerts)
    routine_summary = {
        "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "start_date": start,
        "end_date": end,
        "sources": sources or event_result.get("sources") or [],
        "health_overall_status": health_summary["overall_status"],
        "event_coverage_quality": (event_result.get("coverage") or {}).get("coverage_quality"),
        "events_loaded": event_result.get("events_loaded", 0),
        "events_after_dedup": event_result.get("events_after_dedup", 0),
        "signals_covered_pct": (event_result.get("coverage") or {}).get("signals_with_event_pct", 0),
        "governance_status": (governance_result.get("review") or {}).get("governance_status"),
        "alerts_count": int(len(alerts_df)),
        "message": message,
        "metadata": {"dry_run": dry_run, "with_regimes": with_regimes, "with_event_context": with_event_context, "with_governance": with_governance},
    }
    if status == "SUCCESS" and not alerts_df.empty:
        status = "SUCCESS_WITH_WARNINGS"
        routine_summary["status"] = status
    routine_alerts = build_daily_routine_alerts(routine_summary)
    alerts_df = _concat_alerts([alerts_df, routine_alerts])
    routine_summary["alerts_count"] = int(len(alerts_df))
    report_path = _write_report(routine_summary, health, alerts_df) if write_csv else None
    routine_summary["report_path"] = str(report_path) if report_path else ""
    routine_id = None
    alerts_saved = 0
    if save_db and not dry_run:
        alerts_saved = save_alerts(db_path, alerts_df)
        routine_id = _save_routine_run(db_path, routine_summary)

    print("\nDAILY QUANT ROUTINE")
    print(f"Status: {routine_summary['status']}")
    print(f"Health: {routine_summary['health_overall_status']}")
    print(f"Cobertura eventos: {routine_summary.get('event_coverage_quality') or '-'}")
    print(f"Alertas: {routine_summary['alerts_count']}")
    if routine_id:
        print(f"daily_routine_run_id={routine_id}; alertas_salvos={alerts_saved}")
    if report_path:
        print(f"Relatório: {report_path}")
    return {
        "summary": routine_summary,
        "health": health,
        "health_summary": health_summary,
        "event_result": event_result,
        "governance_result": governance_result,
        "alerts": alerts_df,
        "routine_id": routine_id,
        "alerts_saved": alerts_saved,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotina diária operacional do scanner quantitativo.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--sources", nargs="*", default=None)
    parser.add_argument("--with-regimes", action="store_true")
    parser.add_argument("--with-event-context", action="store_true")
    parser.add_argument("--with-governance", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default="config/events.yaml")
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        sources=args.sources,
        with_regimes=args.with_regimes,
        with_event_context=args.with_event_context,
        with_governance=args.with_governance,
        save_db=args.save_db,
        write_csv=args.write_csv,
        fail_on_error=args.fail_on_error,
        dry_run=args.dry_run,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
