"""Gerar relatório Markdown do diagnóstico fino de custos salvo."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.fine_cost_diagnostics_store import (
    load_exit_rule_cost_diagnostics,
    load_lifecycle_costs,
    load_order_reason_diagnostics,
    load_rebalance_cost_diagnostics,
    load_unknown_cost_diagnostics,
)
from src.paper.position_cost_lifecycle import summarize_lifecycle_costs
from src.reports.fine_cost_diagnostics_report import save_fine_cost_diagnostics_markdown
from src.utils import load_config, project_path


def run(paper_run_id: int, output: str | Path | None = None, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    lifecycle = load_lifecycle_costs(db, run_id=paper_run_id)
    unknown = load_unknown_cost_diagnostics(db, run_id=paper_run_id)
    unknown_summary = unknown.iloc[0].to_dict() if not unknown.empty else {}
    fixes = []
    try:
        fixes = json.loads(unknown_summary.get("required_metadata_fixes_json") or "[]")
    except json.JSONDecodeError:
        fixes = []
    result = {
        "order_reasons": load_order_reason_diagnostics(db, run_id=paper_run_id),
        "lifecycle": lifecycle,
        "lifecycle_summary": summarize_lifecycle_costs(lifecycle),
        "rebalance": {"summary": (load_rebalance_cost_diagnostics(db, run_id=paper_run_id).iloc[0].to_dict() if not load_rebalance_cost_diagnostics(db, run_id=paper_run_id).empty else {}), "rebalance_cost_by_ticker": load_rebalance_cost_diagnostics(db, run_id=paper_run_id)},
        "exit_rules": load_exit_rule_cost_diagnostics(db, run_id=paper_run_id),
        "unknown": {"summary": unknown_summary},
        "metadata_fixes": fixes,
        "rebalance_suggestions": [],
    }
    out = Path(output) if output else project_path("data/reports") / f"fine_cost_diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = save_fine_cost_diagnostics_markdown(out, result)
    return {"paper_run_id": paper_run_id, "report_path": str(path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gerar relatório de diagnóstico fino de custos. Não recomendação.")
    parser.add_argument("--paper-run-id", type=int, required=True)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print(f"Relatório: {result['report_path']}")
    print("Não recomendação: relatório analítico, sem ordens reais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
