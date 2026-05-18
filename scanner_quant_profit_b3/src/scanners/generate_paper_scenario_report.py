"""Gera relatorio markdown da validacao multi-cenario do paper trading."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.paper.paper_scenario_store import (
    load_paper_cost_sensitivity_results,
    load_paper_scenario_validation_results,
    load_paper_scenario_validation_runs,
    load_paper_signal_source_comparison,
)
from src.reports.paper_scenario_validation_report import save_paper_scenario_validation_report
from src.utils import load_config, project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio de validacao multi-cenario.")
    parser.add_argument("--output-dir", default="data/reports/paper_scenario_validation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    db = project_path(cfg["database_path"])
    runs = load_paper_scenario_validation_runs(db)
    run = runs.iloc[0].to_dict() if not runs.empty else {}
    run_id = int(run["id"]) if run else None
    path = save_paper_scenario_validation_report(
        Path(args.output_dir),
        run,
        load_paper_scenario_validation_results(db, run_id),
        load_paper_cost_sensitivity_results(db, run_id),
        load_paper_signal_source_comparison(db, run_id),
        pd.DataFrame(),
    )
    print(f"Relatorio gerado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
