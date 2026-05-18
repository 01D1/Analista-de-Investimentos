"""CLI para gerar relatório Markdown de paper trading."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.paper.paper_store import (
    load_paper_equity_curve,
    load_paper_exit_events,
    load_paper_orders,
    load_paper_pnl_attribution,
    load_paper_positions,
    load_paper_rebalance_events,
    load_paper_simulation_runs,
)
from src.reports.paper_trading_report import save_paper_trading_report
from src.utils import load_config, project_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatório de paper trading.")
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--output-dir", default="data/reports/paper_trading")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = project_path(load_config()["database_path"])
    runs = load_paper_simulation_runs(db)
    if runs.empty:
        print("Nenhum run de paper trading encontrado.")
        return 0
    run = runs[runs["id"] == args.run_id].iloc[0] if args.run_id and (runs["id"] == args.run_id).any() else runs.iloc[0]
    run_id = int(run["id"])
    path = save_paper_trading_report(
        run.to_dict(),
        load_paper_orders(db, run_id),
        load_paper_positions(db, run_id),
        load_paper_equity_curve(db, run_id),
        project_path(args.output_dir),
        load_paper_exit_events(db, run_id),
        load_paper_rebalance_events(db, run_id),
        load_paper_pnl_attribution(db, run_id),
    )
    print(f"Relatório salvo: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
