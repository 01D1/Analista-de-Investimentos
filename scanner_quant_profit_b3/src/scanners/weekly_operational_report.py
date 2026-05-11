"""CLI para relatório semanal operacional."""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.context.coverage_trends import calculate_event_coverage_trend
from src.context.routine_observability import summarize_daily_routine_runs
from src.context.source_quality_contracts import evaluate_source_contracts, load_source_quality_contracts
from src.context.source_sla import calculate_source_sla
from src.notifications.alert_analytics import summarize_alerts
from src.reports.weekly_operational_report import build_weekly_operational_report, save_weekly_report
from src.utils import load_config, project_path


def _read_table(db_path: Path, table: str) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table}", con)
    except Exception:
        return pd.DataFrame()


def _write_aux_csv(output_dir: str | Path, frames: dict[str, pd.DataFrame]) -> list[Path]:
    out_dir = Path(output_dir)
    if not out_dir.is_absolute():
        out_dir = project_path(str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []
    for name, df in frames.items():
        path = out_dir / f"weekly_{name}_{stamp}.csv"
        df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        paths.append(path)
    return paths


def run(*, window_days: int = 7, save_md: bool = False, write_csv: bool = False, output_dir: str = "data/reports", include_governance: bool = False):
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    health = _read_table(db_path, "source_health_checks")
    alerts = _read_table(db_path, "operational_alerts")
    daily_runs = _read_table(db_path, "daily_routine_runs")
    coverage_runs = _read_table(db_path, "event_coverage_runs")
    governance = _read_table(db_path, "governance_reviews") if include_governance else pd.DataFrame()

    source_sla = calculate_source_sla(health, window_days=window_days)
    routine_summary = summarize_daily_routine_runs(daily_runs, window_days=window_days)
    alert_summary = summarize_alerts(alerts, window_days=window_days)
    coverage_trend = calculate_event_coverage_trend(coverage_runs)
    contracts = evaluate_source_contracts(health, coverage_runs, load_source_quality_contracts())
    markdown = build_weekly_operational_report(source_sla, routine_summary, alert_summary, coverage_trend, contracts, governance)
    md_path = save_weekly_report(markdown, output_dir) if save_md else None
    csv_paths = _write_aux_csv(output_dir, {"source_sla": source_sla, "contracts": contracts, "coverage_trend": coverage_trend}) if write_csv else []

    print("\nWEEKLY OPERATIONAL REPORT")
    print(f"Janela: {window_days} dias")
    print(f"Fontes avaliadas: {len(source_sla)}")
    print(f"Alertas totais: {alert_summary.get('total_alerts', 0)}")
    print(f"Saúde da rotina: {routine_summary.get('routine_health_status')}")
    print(f"Contratos com falha/warning: {int(contracts['contract_status'].astype(str).str.upper().isin(['FAIL', 'WARNING']).sum()) if not contracts.empty else 0}")
    if md_path:
        print(f"Relatório Markdown: {md_path}")
    for path in csv_paths:
        print(f"CSV: {path}")
    return {"markdown": markdown, "markdown_path": md_path, "csv_paths": csv_paths, "contracts": contracts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Relatório semanal operacional do scanner quantitativo.")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--save-md", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--output-dir", default="data/reports")
    parser.add_argument("--include-governance", action="store_true")
    args = parser.parse_args()
    run(window_days=args.window_days, save_md=args.save_md, write_csv=args.write_csv, output_dir=args.output_dir, include_governance=args.include_governance)


if __name__ == "__main__":
    main()
