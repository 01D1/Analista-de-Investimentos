"""CLI de reconciliacao B3 raw versus SQLite."""
from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.b3_reconciliation import compare_b3_raw_vs_sqlite, generate_b3_reconciliation_report, summarize_b3_raw_files, summarize_b3_sqlite
from src.data_quality.reconciliation_store import save_reconciliation_run
from src.utils import load_config, project_path


def _write_csv(df: pd.DataFrame, prefix: str) -> Path | None:
    if df is None or df.empty:
        return None
    out = project_path("data/reports")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def run(
    *,
    year: int | None = None,
    raw_dir: str | Path = "data/raw",
    db_path: str | Path | None = None,
    csv: bool = False,
    save_db: bool = False,
    suggest_fixes: bool = False,
    execute_fixes: bool = False,
    confirm: bool = False,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    raw = summarize_b3_raw_files(raw_dir)
    if year is not None and not raw.empty:
        raw = raw[raw["year"].astype(str) == str(year)].copy()
    sqlite = summarize_b3_sqlite(db)
    results = compare_b3_raw_vs_sqlite(raw, sqlite)
    executed = 0
    if execute_fixes and confirm:
        commands = results["suggested_command"].dropna().astype(str)
        for command in commands:
            if not command.startswith("python -m src.collectors.b3_cotahist_collector"):
                continue
            proc = subprocess.run(command.split(), cwd=project_path("."), capture_output=True, text=True, timeout=600)
            executed += 1
            mask = results["suggested_command"] == command
            results.loc[mask, "executed"] = True
            results.loc[mask, "execution_status"] = "SUCCESS" if proc.returncode == 0 else "FAILED"
    summary = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "reconciliation_type": "b3",
        "status": "OK" if results["issue_type"].eq("OK").all() else "WARNING",
        "issues_count": int((results["issue_type"] != "OK").sum()),
        "fixes_suggested_count": int(results["suggested_command"].astype(str).str.len().gt(0).sum()),
        "fixes_executed_count": executed,
    }
    run_id = save_reconciliation_run(db, summary, results) if save_db else 0
    csv_path = _write_csv(results, "b3_reconciliation") if csv else None
    print("\nB3 RECONCILIATION")
    print(generate_b3_reconciliation_report(results))
    print(f"Issues: {summary['issues_count']} | Fixes sugeridos: {summary['fixes_suggested_count']} | Executados: {executed}")
    if execute_fixes and not confirm:
        print("Execucao bloqueada: use --execute-fixes --confirm para reprocessar.")
    if csv_path:
        print(f"CSV: {csv_path}")
    if run_id:
        print(f"Run salvo: {run_id}")
    return {"raw": raw, "sqlite": sqlite, "results": results, "summary": summary, "run_id": run_id, "csv_path": csv_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcilia B3 COTAHIST raw versus SQLite.")
    parser.add_argument("--year", type=int)
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--db-path")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--suggest-fixes", action="store_true")
    parser.add_argument("--execute-fixes", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run(year=args.year, raw_dir=args.raw_dir, db_path=args.db_path, csv=args.csv, save_db=args.save_db, suggest_fixes=args.suggest_fixes, execute_fixes=args.execute_fixes, confirm=args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

