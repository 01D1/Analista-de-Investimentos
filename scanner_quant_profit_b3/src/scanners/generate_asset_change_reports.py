"""CLI para gerar relatórios Markdown de mudanças do snapshot integrado."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.integration.asset_intelligence_diff_store import load_asset_intelligence_diff_history
from src.integration.asset_intelligence_history import build_asset_history
from src.integration.asset_intelligence_store import load_asset_intelligence_history
from src.reports.asset_intelligence_change_report import save_asset_change_report
from src.utils import load_config, project_path


def run(tickers: list[str] | None, output_dir: str | Path, db_path: str | Path | None = None) -> list[Path]:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    snapshots = load_asset_intelligence_history(db, limit=5000)
    if tickers is None or not tickers:
        tickers = sorted(snapshots["ticker"].dropna().astype(str).unique().tolist()) if not snapshots.empty else []
    out_dir = project_path(str(output_dir)) if not Path(output_dir).is_absolute() else Path(output_dir)
    paths = []
    for ticker in tickers:
        history = build_asset_history(snapshots, ticker)
        diffs = load_asset_intelligence_diff_history(db, ticker=ticker, limit=500)
        if history.empty and diffs.empty:
            continue
        paths.append(save_asset_change_report(ticker, history, diffs, out_dir))
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatórios de histórico da inteligência integrada.")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--output-dir", default="data/reports/asset_intelligence_changes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = run(args.tickers, args.output_dir)
    print("ASSET INTELLIGENCE CHANGE REPORTS")
    print(f"Relatórios gerados: {len(paths)}")
    for path in paths:
        print(f"- {path}")
    if not paths:
        print("Histórico insuficiente para gerar relatórios de mudança.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
