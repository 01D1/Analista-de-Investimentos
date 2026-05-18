"""CLI para comparar duas simulacoes paper: simple vs advanced."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.paper_store import load_paper_equity_curve, load_paper_orders, load_paper_simulation_runs
from src.paper.paper_walk_forward_store import save_paper_simulation_comparison
from src.paper.simulation_comparison import compare_paper_simulations, generate_simulation_comparison_report
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame, stem: str) -> Path | None:
    if df is None or df.empty:
        return None
    path = _reports_dir() / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _find_run(runs: pd.DataFrame, run_id: int) -> dict:
    if runs is None or runs.empty:
        return {}
    row = runs[pd.to_numeric(runs["id"], errors="coerce") == int(run_id)]
    return row.iloc[0].to_dict() if not row.empty else {}


def _enrich_run(db_path: str | Path, row: dict, run_id: int) -> dict:
    enriched = dict(row)
    orders = load_paper_orders(db_path, run_id)
    equity = load_paper_equity_curve(db_path, run_id)
    if not orders.empty:
        status = orders.get("order_status", pd.Series(dtype=str)).astype(str)
        enriched["turnover"] = int((status == "SIMULATED_FILLED").sum())
        enriched["trades_count"] = enriched.get("trades_count") or enriched["turnover"]
    if not equity.empty:
        enriched["exposure_avg"] = float(pd.to_numeric(equity.get("exposure"), errors="coerce").fillna(0).mean())
        enriched["var_avg"] = float(pd.to_numeric(equity.get("portfolio_var_95"), errors="coerce").fillna(0).mean())
        enriched["es_avg"] = float(pd.to_numeric(equity.get("portfolio_es_95"), errors="coerce").fillna(0).mean())
    return enriched


def run(
    simple_run_id: int,
    advanced_run_id: int,
    save_db: bool = False,
    csv: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    runs = load_paper_simulation_runs(db, limit=5000)
    simple = _enrich_run(db, _find_run(runs, simple_run_id), simple_run_id)
    advanced = _enrich_run(db, _find_run(runs, advanced_run_id), advanced_run_id)
    comparison = compare_paper_simulations(simple, advanced)
    report = generate_simulation_comparison_report(comparison)
    saved_rows = 0
    if save_db:
        init_database(db, verbose=False)
        saved_rows = save_paper_simulation_comparison(db, simple_run_id, advanced_run_id, comparison)
    csv_path = str(_write_csv(comparison, "paper_simulation_comparison") or "") if csv else ""
    return {"rows": int(len(comparison)), "saved_rows": saved_rows, "csv_path": csv_path, "report": report, "comparison_df": comparison}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compara simulacoes simple vs advanced de paper trading.")
    parser.add_argument("--simple-run-id", type=int, required=True)
    parser.add_argument("--advanced-run-id", type=int, required=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(args.simple_run_id, args.advanced_run_id, save_db=args.save_db, csv=args.csv)
    print("PAPER SIMULATION COMPARISON")
    print(summary["report"])
    print(f"Metricas comparadas: {summary['rows']}")
    if summary["saved_rows"]:
        print(f"Linhas salvas: {summary['saved_rows']}")
    if summary["csv_path"]:
        print(f"CSV: {summary['csv_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
