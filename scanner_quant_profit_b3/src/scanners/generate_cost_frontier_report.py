"""Gerar relatório Markdown da fronteira custo-retorno-drawdown."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.paper.cost_frontier_store import load_cost_frontier_results, load_cost_frontier_runs
from src.reports.cost_frontier_report import save_cost_frontier_report
from src.utils import load_config, project_path


def run(run_id: int | None = None, output: str | Path | None = None, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    runs = load_cost_frontier_runs(db)
    if runs.empty:
        source_id = 0
        results = load_cost_frontier_results(db, run_id=run_id)
    else:
        selected = runs[runs["id"].astype(int).eq(int(run_id))].iloc[0] if run_id is not None and (runs["id"].astype(int).eq(int(run_id))).any() else runs.iloc[0]
        run_id = int(selected["id"])
        source_id = int(selected.get("source_cost_reduction_run_id") or 0)
        results = load_cost_frontier_results(db, run_id=run_id)
    out = Path(output) if output else project_path("data/reports") / f"cost_frontier_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = save_cost_frontier_report(out, source_id, results)
    return {"run_id": run_id, "report_path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gerar relatório de fronteira de custo. Não recomendação.")
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print(f"Relatório: {result['report_path']}")
    print("Não recomendação: relatório analítico, sem ordens reais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
