"""Gera relatorio markdown de validacao OOS de hipoteses."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.paper.hypothesis_oos_store import load_hypothesis_oos_coverage, load_hypothesis_oos_results, load_hypothesis_oos_runs
from src.reports.hypothesis_oos_report import generate_hypothesis_oos_report
from src.utils import load_config, project_path


def run(run_id: int | None = None, output_dir: str | Path = "data/reports/hypothesis_oos", db_path: str | Path | None = None) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    runs = load_hypothesis_oos_runs(db)
    if runs.empty:
        return {"status": "INSUFFICIENT_DATA", "path": None}
    if run_id is None:
        run_id = int(runs.iloc[0]["id"])
        run_row = runs.iloc[0]
    else:
        matches = runs[runs["id"].astype(int) == int(run_id)]
        if matches.empty:
            return {"status": "INSUFFICIENT_DATA", "path": None}
        run_row = matches.iloc[0]
    results = load_hypothesis_oos_results(db, run_id=run_id)
    coverage = load_hypothesis_oos_coverage(db, run_id=run_id)
    output = project_path(output_dir) if not Path(output_dir).is_absolute() else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"hypothesis_oos_report_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(generate_hypothesis_oos_report(run_row, results, coverage), encoding="utf-8")
    return {"status": "COMPLETED", "path": str(path), "run_id": run_id}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio OOS de hipotese.")
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--output-dir", default="data/reports/hypothesis_oos")
    return parser


def main(argv: list[str] | None = None) -> int:
    summary = run(**vars(build_parser().parse_args(argv)))
    print("HYPOTHESIS OOS REPORT")
    print(f"Status: {summary['status']}")
    if summary.get("path"):
        print(f"Relatorio: {summary['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
