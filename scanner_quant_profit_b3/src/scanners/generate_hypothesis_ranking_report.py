"""CLI para gerar relatório Markdown do ranking de hipóteses."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.paper.hypothesis_ranking_store import load_hypothesis_ranking_results, load_hypothesis_ranking_runs
from src.reports.hypothesis_ranking_report import save_hypothesis_ranking_markdown
from src.utils import load_config, project_path


def run(run_id: int | None = None, output: str | Path | None = None, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    runs = load_hypothesis_ranking_runs(db)
    selected = int(run_id or (runs.iloc[0]["id"] if not runs.empty else 0))
    ranked = load_hypothesis_ranking_results(db, run_id=selected) if selected else load_hypothesis_ranking_results(db)
    out = Path(output) if output else project_path("data/reports") / f"hypothesis_ranking_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = save_hypothesis_ranking_markdown(out, ranked)
    return {"run_id": selected, "path": str(path), "rows": int(len(ranked))}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório Markdown do ranking de hipóteses.")
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--output", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(**vars(args))
    print("HYPOTHESIS RANKING REPORT")
    print(f"Run: {result['run_id']}")
    print(f"Linhas: {result['rows']}")
    print(f"Relatório: {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

