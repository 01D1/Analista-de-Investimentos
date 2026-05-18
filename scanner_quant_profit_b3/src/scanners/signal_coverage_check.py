"""CLI de validação de cobertura das fontes de sinal em estudo."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.signals.signal_coverage import analyze_signal_coverage, generate_signal_coverage_report
from src.signals.signal_coverage_requirements import evaluate_signal_coverage_requirements
from src.signals.signal_coverage_store import save_signal_coverage_run
from src.utils import load_config, project_path


def _write_csv(df: pd.DataFrame) -> str:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"signal_coverage_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return str(path)


def run(
    start: str | None = None,
    end: str | None = None,
    sources: list[str] | None = None,
    save_db: bool = False,
    csv: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    coverage = analyze_signal_coverage(db, start, end, sources=sources)
    coverage = evaluate_signal_coverage_requirements(coverage)
    run_id = save_signal_coverage_run(db, coverage, start, end, sources_checked=sources) if save_db else None
    csv_path = _write_csv(coverage) if csv else ""
    return {
        "coverage": coverage,
        "report": generate_signal_coverage_report(coverage),
        "saved_run_id": run_id,
        "csv_path": csv_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Checa cobertura mínima por fonte e regime.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--sources", nargs="+", default=["quant", "technical", "integrated"])
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(**vars(args))
    print("SIGNAL COVERAGE CHECK")
    print(result["report"])
    if result["saved_run_id"]:
        print(f"Run salvo: {result['saved_run_id']}")
    if result["csv_path"]:
        print(f"CSV: {result['csv_path']}")
    print("Validação de amostra: cobertura insuficiente bloqueia conclusão de robustez.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

