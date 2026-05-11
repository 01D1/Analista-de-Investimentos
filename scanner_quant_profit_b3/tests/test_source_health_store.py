from datetime import datetime

import pandas as pd

from src.context.source_health_store import (
    load_latest_source_health_checks,
    load_source_health_history,
    save_source_health_checks,
    summarize_source_health,
)
from src.db.init_db import init_database


def _health_df():
    return pd.DataFrame(
        [
            {
                "source_name": "csv",
                "status": "OK",
                "available": True,
                "records_count": 3,
                "latest_date": datetime.now().strftime("%Y-%m-%d"),
                "age_days": 0,
                "coverage_hint": "usable",
                "path": "events.csv",
                "message": "ok",
                "checked_at": "2026-01-01T10:00:00",
                "metadata_json": "{}",
            },
            {
                "source_name": "news_hunter",
                "status": "MISSING",
                "available": False,
                "records_count": 0,
                "latest_date": None,
                "age_days": None,
                "coverage_hint": "verificar_fonte",
                "path": "banco.db",
                "message": "missing",
                "checked_at": "2026-01-01T10:00:00",
                "metadata_json": "{}",
            },
        ]
    )


def test_save_and_load_source_health_checks(tmp_path):
    db_path = tmp_path / "scanner.db"
    init_database(db_path, verbose=False)

    saved = save_source_health_checks(db_path, _health_df())
    latest = load_latest_source_health_checks(db_path)
    history = load_source_health_history(db_path, source_name="csv")

    assert saved == 2
    assert len(latest) == 2
    assert history.loc[0, "source_name"] == "csv"


def test_summarize_source_health_flags_error():
    summary = summarize_source_health(_health_df())

    assert summary["total_sources"] == 2
    assert summary["missing_count"] == 1
    assert summary["overall_status"] == "ERROR"
