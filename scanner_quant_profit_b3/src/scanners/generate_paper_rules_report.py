"""Gera relatorio markdown de robustez das regras de paper trading."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.paper.paper_oos_governance import evaluate_paper_oos_governance
from src.paper.paper_walk_forward_store import (
    load_paper_exit_optimization_results,
    load_paper_exit_optimization_runs,
    load_paper_simulation_comparisons,
    load_paper_walk_forward_results,
    load_paper_walk_forward_runs,
)
from src.reports.paper_rules_robustness_report import save_paper_rules_robustness_report
from src.utils import load_config, project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatorio de robustez de regras simuladas.")
    parser.add_argument("--output-dir", default="data/reports/paper_rules")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    db = project_path(cfg["database_path"])
    wf_runs = load_paper_walk_forward_runs(db)
    wf_run = wf_runs.iloc[0].to_dict() if not wf_runs.empty else {}
    wf_run_id = int(wf_run["id"]) if wf_run else None
    wf_results = load_paper_walk_forward_results(db, wf_run_id)
    opt_runs = load_paper_exit_optimization_runs(db)
    opt_run_id = int(opt_runs.iloc[0]["id"]) if not opt_runs.empty else None
    opt_results = load_paper_exit_optimization_results(db, opt_run_id)
    comparison = load_paper_simulation_comparisons(db)
    metadata = {}
    if wf_run.get("metadata_json"):
        try:
            metadata = json.loads(wf_run["metadata_json"])
        except json.JSONDecodeError:
            metadata = {}
    governance = metadata.get("governance") or evaluate_paper_oos_governance(wf_run)
    path = save_paper_rules_robustness_report(Path(args.output_dir), comparison, opt_results, wf_results, wf_run, governance)
    print(f"Relatorio gerado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
