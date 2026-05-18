"""CLI do assistente operacional de ingestao."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.ingestion_alerts import build_alerts_from_ingestion_run
from src.data_quality.ingestion_assistant_store import save_ingestion_assistant_run
from src.data_quality.ingestion_comparison import compare_reliability_before_after
from src.data_quality.ingestion_executor import execute_ingestion_plan
from src.data_quality.ingestion_plan import build_ingestion_plan_from_reconciliation, summarize_ingestion_plan
from src.data_quality.post_ingestion_validation import run_post_ingestion_validation
from src.data_quality.source_reliability import calculate_source_reliability_score
from src.notifications.alert_store import save_alerts
from src.reports.ingestion_assistant_report import generate_ingestion_assistant_report
from src.scanners.data_reconciliation import run as run_reconciliation
from src.data_quality.source_inventory import build_source_inventory
from src.utils import load_config, project_path


def _write_csv(df: pd.DataFrame, prefix: str) -> Path | None:
    if df is None or df.empty:
        return None
    out = project_path("data/reports")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _audit() -> pd.DataFrame:
    return calculate_source_reliability_score(build_source_inventory())


def run(
    *,
    sources: list[str] | None = None,
    dry_run: bool = True,
    execute: bool = False,
    confirm: bool = False,
    save_db: bool = False,
    csv: bool = False,
    validate_after: bool = True,
    compare_before_after: bool = True,
    only_step: str | None = None,
    db_path: str | Path | None = None,
) -> dict:
    started_at = datetime.now().isoformat(timespec="seconds")
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    selected = sources or ["b3", "profit", "options", "ri"]
    if "all" in selected:
        selected = ["b3", "profit", "options", "ri"]
    before_audit = _audit()
    recon = run_reconciliation(sources=selected, save_db=False, csv=False, suggest_fixes=True, db_path=db)
    plan = build_ingestion_plan_from_reconciliation(recon["results"])
    if only_step and not plan.empty:
        plan = plan[plan["step_id"].astype(str) == only_step].copy()
    effective_dry_run = dry_run or not execute
    steps = execute_ingestion_plan(plan, dry_run=effective_dry_run, confirm=confirm, only_sources=selected)
    validation = run_post_ingestion_validation(selected, db_path=db) if validate_after else pd.DataFrame()
    after_audit = _audit() if compare_before_after else pd.DataFrame()
    comparison = compare_reliability_before_after(before_audit, after_audit) if compare_before_after else pd.DataFrame()
    plan_summary = summarize_ingestion_plan(plan)
    improvements = int(validation["improvement_detected"].fillna(False).astype(bool).sum()) if not validation.empty else 0
    steps_failed = int(steps["status"].astype(str).str.upper().eq("FAILED").sum()) if not steps.empty else 0
    steps_executed = int(steps["status"].astype(str).str.upper().eq("SUCCESS").sum()) if not steps.empty else 0
    manual_steps = int(steps["status"].astype(str).str.upper().eq("MANUAL_REQUIRED").sum()) if not steps.empty else plan_summary.get("manual_steps", 0)
    status = "FAILED" if steps_failed else ("DRY_RUN" if effective_dry_run else "SUCCESS")
    summary = {
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "dry_run": effective_dry_run,
        "executed": bool(execute and confirm and not effective_dry_run),
        "status": status,
        "sources": ",".join(selected),
        "steps_total": int(len(plan)),
        "steps_executed": steps_executed,
        "steps_failed": steps_failed,
        "manual_steps": manual_steps,
        "improvements_count": improvements,
        "metadata": {"plan_summary": plan_summary},
    }
    run_id = save_ingestion_assistant_run(db, summary, steps, validation, comparison) if save_db else 0
    alerts_saved = save_alerts(db, build_alerts_from_ingestion_run(summary, steps, validation, comparison)) if save_db else 0
    csv_paths = []
    if csv:
        for df, prefix in [
            (plan, "ingestion_plan"),
            (steps, "ingestion_steps"),
            (validation, "post_ingestion_validation"),
            (comparison, "ingestion_reliability_comparison"),
        ]:
            path = _write_csv(df, prefix)
            if path:
                csv_paths.append(str(path))
    report = generate_ingestion_assistant_report(summary, steps, validation, comparison)
    print("\nINGESTION ASSISTANT")
    print(f"Status: {summary['status']} | Fontes: {summary['sources']} | Etapas: {summary['steps_total']}")
    if effective_dry_run:
        print("Modo: DRY-RUN. Nenhum comando foi executado.")
    elif execute and not confirm:
        print("Execucao bloqueada: use --execute --confirm.")
    for _, row in steps.iterrows():
        print(f"{row.get('status')}: {row.get('source_domain')} — {row.get('title')} — {row.get('suggested_command') or 'manual'}")
    if run_id:
        print(f"Run salvo: {run_id}; alertas: {alerts_saved}")
    return {"summary": summary, "plan": plan, "steps": steps, "validation": validation, "comparison": comparison, "run_id": run_id, "alerts_saved": alerts_saved, "csv_paths": csv_paths, "report": report}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assistente operacional de ingestao em modo seguro.")
    parser.add_argument("--sources", nargs="*", default=["b3", "profit", "options", "ri"], choices=["b3", "profit", "options", "ri", "all"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--validate-after", action="store_true", default=True)
    parser.add_argument("--compare-before-after", action="store_true", default=True)
    parser.add_argument("--only-step")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run(sources=args.sources, dry_run=(args.dry_run or not args.execute), execute=args.execute, confirm=args.confirm, save_db=args.save_db, csv=args.csv, validate_after=args.validate_after, compare_before_after=args.compare_before_after, only_step=args.only_step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
