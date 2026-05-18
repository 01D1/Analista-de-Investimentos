"""Gera relatorio Markdown do ultimo run do assistente de ingestao."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from src.data_quality.ingestion_assistant_store import (
    load_ingestion_assistant_runs,
    load_ingestion_assistant_steps,
    load_ingestion_comparison,
    load_post_ingestion_validation,
)
from src.reports.ingestion_assistant_report import generate_ingestion_assistant_report
from src.utils import load_config, project_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera relatorio do assistente de ingestao.")
    parser.add_argument("--output-dir", default="data/reports")
    args = parser.parse_args(argv)
    cfg = load_config()
    db = project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    runs = load_ingestion_assistant_runs(db, limit=1)
    if runs.empty:
        print("Nenhum run do assistente encontrado.")
        return 0
    run_id = int(runs.iloc[0]["id"])
    report = generate_ingestion_assistant_report(runs.iloc[0].to_dict(), load_ingestion_assistant_steps(db, run_id), load_post_ingestion_validation(db, run_id), load_ingestion_comparison(db, run_id))
    out = project_path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"ingestion_assistant_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(report, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

