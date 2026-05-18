"""CLI para gerar relatórios Markdown por ativo a partir do snapshot integrado."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.integration.asset_intelligence_engine import build_asset_intelligence_snapshot
from src.integration.asset_intelligence_store import load_latest_asset_intelligence_snapshot
from src.reports.asset_intelligence_report import save_asset_intelligence_report
from src.utils import load_config, project_path


def run(tickers: list[str] | None, output_dir: str | Path, db_path: str | Path | None = None) -> list[Path]:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    df = load_latest_asset_intelligence_snapshot(db, tickers=tickers)
    if df.empty:
        df = build_asset_intelligence_snapshot(tickers=tickers, db_path=db)
    out_dir = project_path(str(output_dir)) if not Path(output_dir).is_absolute() else Path(output_dir)
    paths = []
    for _, row in df.iterrows():
        paths.append(save_asset_intelligence_report(row, out_dir))
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera relatórios Markdown de inteligência integrada por ativo.")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--output-dir", default="data/reports/asset_intelligence")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = run(args.tickers, args.output_dir)
    print("ASSET INTELLIGENCE REPORTS")
    print(f"Relatórios gerados: {len(paths)}")
    for path in paths:
        print(f"- {path}")
    if not paths:
        print("Nenhum snapshot integrado encontrado para gerar relatórios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
