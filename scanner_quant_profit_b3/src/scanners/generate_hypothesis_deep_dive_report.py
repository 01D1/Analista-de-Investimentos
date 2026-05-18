"""CLI para gerar relatorio Markdown do deep dive de hipoteses."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.paper.hypothesis_deep_store import load_hypothesis_block_reasons, load_hypothesis_deep_oos_results, load_hypothesis_deep_oos_runs
from src.paper.hypothesis_asset_decomposition import decompose_hypothesis_by_asset
from src.paper.hypothesis_signal_source_decomposition import decompose_hypothesis_by_signal_source
from src.reports.hypothesis_deep_dive_report import save_hypothesis_deep_dive_markdown
from src.utils import load_config, project_path


def run(run_id: int | None = None, output: str | None = None, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    runs = load_hypothesis_deep_oos_runs(db)
    selected = int(run_id) if run_id is not None else (int(runs.iloc[0]["id"]) if not runs.empty else None)
    deep = load_hypothesis_deep_oos_results(db, run_id=selected) if selected else load_hypothesis_deep_oos_results(db)
    reasons = load_hypothesis_block_reasons(db, run_id=selected) if selected else load_hypothesis_block_reasons(db)
    assets = decompose_hypothesis_by_asset(deep)
    sources = decompose_hypothesis_by_signal_source(deep)
    out = Path(output) if output else project_path("data/reports") / f"hypothesis_deep_dive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = save_hypothesis_deep_dive_markdown(out, deep, reasons, assets, sources)
    return {"run_id": selected, "rows": int(len(deep)), "path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio de deep dive de hipoteses. Nao recomendacao.")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print(f"Relatorio deep dive gerado: {result['path']} ({result['rows']} linhas, run={result['run_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
