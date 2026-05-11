from datetime import datetime

import pandas as pd

from src.context.source_health import check_all_sources, check_csv_health, check_news_hunter_health
from src.context.source_health_store import summarize_source_health


def _config(csv_path=None, news_path=None):
    return {
        "sources": {
            "csv": {"path": str(csv_path) if csv_path else "missing.csv"},
            "news_hunter": {"db_path": str(news_path) if news_path else "missing.db"},
            "macro_calendar": {"path": "missing.json"},
            "cvm": {"base_dir": "missing_cvm"},
            "releases": {"base_dir": "missing_releases"},
        },
        "health": {"max_stale_days": 45, "warning_stale_days": 15, "min_csv_records": 1},
    }


def test_check_csv_health_existing_file_ok(tmp_path):
    csv_path = tmp_path / "events.csv"
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path.write_text(f"event_date,ticker,event_title\n{today},PETR4,Evento\n", encoding="utf-8")

    health = check_csv_health(_config(csv_path=csv_path))

    assert health["source_name"] == "csv"
    assert health["status"] == "OK"
    assert health["records_count"] == 1


def test_check_csv_health_missing_file():
    health = check_csv_health(_config())

    assert health["status"] == "MISSING"
    assert health["available"] is False


def test_check_news_hunter_health_missing_database():
    health = check_news_hunter_health(_config())

    assert health["source_name"] == "news_hunter"
    assert health["status"] == "MISSING"


def test_check_all_sources_and_summary(tmp_path):
    config_path = tmp_path / "events.yaml"
    csv_path = tmp_path / "events.csv"
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path.write_text(f"event_date,ticker,event_title\n{today},PETR4,Evento\n", encoding="utf-8")
    config_path.write_text(
        f"""
sources:
  csv:
    enabled: true
    path: "{csv_path.as_posix()}"
health:
  max_stale_days: 45
  warning_stale_days: 15
""",
        encoding="utf-8",
    )

    health_df = check_all_sources(config_path)
    summary = summarize_source_health(health_df)

    assert "csv" in health_df["source_name"].tolist()
    assert summary["total_sources"] == 5
    assert summary["overall_status"] in {"WARNING", "ERROR"}
