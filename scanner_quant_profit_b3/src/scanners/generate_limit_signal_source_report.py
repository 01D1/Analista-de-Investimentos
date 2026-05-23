"""CLI para relatório de calibração LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.paper.limit_signal_source_ranking import rank_limit_signal_source_variants
from src.paper.limit_signal_source_store import load_limit_signal_source_variant_results, load_limit_signal_source_variant_runs
from src.paper.limit_signal_source_variants import build_limit_signal_source_variants
from src.reports.limit_signal_source_report import save_limit_signal_source_markdown
from src.utils import load_config, project_path


def run(run_id: int | None = None, output: str | None = None, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    runs = load_limit_signal_source_variant_runs(db)
    selected = int(run_id) if run_id is not None else (int(runs.iloc[0]["id"]) if not runs.empty else None)
    oos = load_limit_signal_source_variant_results(db, run_id=selected) if selected else load_limit_signal_source_variant_results(db)
    ranked = rank_limit_signal_source_variants(oos)
    variants = build_limit_signal_source_variants()
    out = Path(output) if output else project_path("data/reports") / f"limit_signal_source_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = save_limit_signal_source_markdown(out, ranked, oos, variants)
    return {"run_id": selected, "rows": int(len(oos)), "path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório LIMIT_SIGNAL_SOURCE. Não recomendação.")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print(f"Relatório LIMIT_SIGNAL_SOURCE gerado: {result['path']} ({result['rows']} linhas, run={result['run_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
