"""Gera relatorio markdown de fragilidade da carteira simulada."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.paper.paper_fragility_store import (
    load_paper_drawdown_periods,
    load_paper_fragility_by_asset,
    load_paper_fragility_by_signal_source,
    load_paper_fragility_runs,
)
from src.reports.paper_fragility_report import save_paper_fragility_report
from src.utils import load_config, project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio de fragilidade do paper trading.")
    parser.add_argument("--output-dir", default="data/reports/paper_fragility")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    db = project_path(cfg["database_path"])
    runs = load_paper_fragility_runs(db)
    run = runs.iloc[0].to_dict() if not runs.empty else {}
    run_id = int(run["id"]) if run else None
    path = save_paper_fragility_report(
        Path(args.output_dir),
        run,
        load_paper_fragility_by_asset(db, run_id),
        load_paper_fragility_by_signal_source(db, run_id),
        load_paper_drawdown_periods(db, run_id),
    )
    print(f"Relatorio gerado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
