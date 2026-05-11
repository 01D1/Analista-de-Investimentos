"""CLI de health check das fontes de eventos."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.context.source_health import check_all_sources
from src.context.source_health_store import save_source_health_checks, summarize_source_health
from src.utils import load_config, project_path


def _write_csv(health_df: pd.DataFrame) -> Path:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"source_health_checks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    health_df.to_csv(path, index=False, sep=";", decimal=",")
    return path


def run(
    *,
    config_path: str | Path = "config/events.yaml",
    save_db: bool = False,
    write_csv: bool = False,
    fail_on_error: bool = False,
    verbose: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    health = check_all_sources(config_path)
    summary = summarize_source_health(health)
    cfg = load_config()
    db_path = Path(db_path) if db_path else project_path(cfg["database_path"])
    saved = save_source_health_checks(db_path, health) if save_db else 0
    csv_path = _write_csv(health) if write_csv else None

    print("\nSOURCE HEALTH CHECK")
    for _, row in health.iterrows():
        print(
            f"{row.get('status')}: {row.get('source_name')} — "
            f"{int(row.get('records_count') or 0)} registros — latest_date {row.get('latest_date') or '-'}"
        )
        if verbose:
            print(f"  {row.get('message')} | {row.get('path')}")
    print(f"\nOverall status: {summary['overall_status']}")
    if save_db:
        print(f"Health checks salvos: {saved}")
    if csv_path:
        print(f"CSV gerado: {csv_path}")

    exit_code = 1 if fail_on_error and summary["overall_status"] == "ERROR" else 0
    return {"health": health, "summary": summary, "saved": saved, "csv_path": csv_path, "exit_code": exit_code}


def main() -> None:
    parser = argparse.ArgumentParser(description="Health check das fontes locais de eventos.")
    parser.add_argument("--config", default="config/events.yaml")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    result = run(
        config_path=args.config,
        save_db=args.save_db,
        write_csv=args.write_csv,
        fail_on_error=args.fail_on_error,
        verbose=args.verbose,
    )
    if result["exit_code"]:
        sys.exit(result["exit_code"])


if __name__ == "__main__":
    main()
