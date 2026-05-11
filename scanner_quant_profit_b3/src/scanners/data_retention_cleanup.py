"""CLI de retenção e limpeza segura de tabelas operacionais."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.notifications.alert_engine import build_alerts_from_retention_cleanup
from src.notifications.alert_store import save_alerts
from src.ops.data_retention import run_retention_cleanup
from src.ops.retention_policy import load_retention_policy, validate_retention_policy
from src.ops.retention_store import save_retention_cleanup_run
from src.utils import load_config, project_path


def _write_csv(summary: dict, details: pd.DataFrame) -> Path:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports / f"retention_cleanup_{stamp}.csv"
    out = details.copy()
    for key, value in summary.items():
        if key not in {"warnings", "errors"}:
            out[f"summary_{key}"] = value
    out.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def run(*, config_path: str = "config/retention.yaml", dry_run: bool = True, execute: bool = False, confirm: bool = False, archive: bool = True, save_db: bool = False, write_csv: bool = False):
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    policy = load_retention_policy(config_path)
    errors = validate_retention_policy(policy)
    if errors:
        summary = {
            "dry_run": 1,
            "status": "FAILED",
            "tables_evaluated": 0,
            "rows_candidates": 0,
            "rows_archived": 0,
            "rows_deleted": 0,
            "archive_dir": "",
            "warnings": [],
            "errors": errors,
            "warnings_count": 0,
            "errors_count": len(errors),
        }
        details = pd.DataFrame()
    else:
        effective_dry_run = True if dry_run or not execute else False
        summary, details = run_retention_cleanup(db_path, policy, dry_run=effective_dry_run, confirm=confirm, archive=archive)
    csv_path = _write_csv(summary, details) if write_csv else None
    run_id = save_retention_cleanup_run(db_path, summary, details) if save_db else None
    if save_db:
        save_alerts(db_path, build_alerts_from_retention_cleanup(summary))

    print("\nDATA RETENTION CLEANUP")
    print(f"Modo: {'DRY-RUN' if summary.get('dry_run') else 'EXECUTE'}")
    print(f"Status: {summary.get('status')}")
    print(f"Tabelas avaliadas: {summary.get('tables_evaluated', 0)}")
    print(f"Linhas candidatas: {summary.get('rows_candidates', 0)}")
    print(f"Linhas deletadas: {summary.get('rows_deleted', 0)}")
    print(f"Linhas arquivadas: {summary.get('rows_archived', 0)}")
    protected = int(details.get("protected", pd.Series(dtype=int)).fillna(0).sum()) if not details.empty and "protected" in details.columns else 0
    print(f"Tabelas protegidas ignoradas: {protected}")
    if run_id:
        print(f"Run salvo: retention_cleanup_run_id={run_id}")
    if csv_path:
        print(f"CSV gerado: {csv_path}")
    for warning in summary.get("warnings", []):
        print(f"WARNING: {warning}")
    for error in summary.get("errors", []):
        print(f"ERROR: {error}")
    return {"summary": summary, "details": details, "run_id": run_id, "csv_path": csv_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Retenção segura das tabelas operacionais.")
    parser.add_argument("--config", default="config/retention.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    args = parser.parse_args()
    run(
        config_path=args.config,
        dry_run=args.dry_run or not args.execute,
        execute=args.execute,
        confirm=args.confirm,
        archive=args.archive,
        save_db=args.save_db,
        write_csv=args.write_csv,
    )


if __name__ == "__main__":
    main()
