"""Gera relatorio markdown das investigacoes de paper trading."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.investigation_store import load_investigation_results, load_investigation_runs
from src.reports.paper_investigation_report import generate_paper_investigation_report
from src.utils import load_config, project_path


def run(run_id: int | None = None, output_dir: str | Path = "data/reports/paper_investigations", db_path: str | Path | None = None) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    runs = load_investigation_runs(db)
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
    results = load_investigation_results(db, run_id=run_id)
    hypotheses_cols = ["hypothesis_id", "hypothesis_type", "target", "title", "metadata_json"]
    hypotheses = results[hypotheses_cols].copy() if not results.empty else pd.DataFrame(columns=hypotheses_cols)
    output = project_path(output_dir) if not Path(output_dir).is_absolute() else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"paper_investigation_report_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(generate_paper_investigation_report(run_row, hypotheses, results), encoding="utf-8")
    return {"status": "COMPLETED", "path": str(path), "run_id": run_id}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio de investigacoes da carteira simulada.")
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--output-dir", default="data/reports/paper_investigations")
    return parser


def main(argv: list[str] | None = None) -> int:
    summary = run(**vars(build_parser().parse_args(argv)))
    print("PAPER INVESTIGATION REPORT")
    print(f"Status: {summary['status']}")
    if summary.get("path"):
        print(f"Relatorio: {summary['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
