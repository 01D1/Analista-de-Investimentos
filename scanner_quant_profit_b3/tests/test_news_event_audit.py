import sqlite3

from src.data_quality.news_event_audit import audit_event_pipeline, audit_news_hunter


def test_news_hunter_missing(tmp_path):
    result = audit_news_hunter(tmp_path / "missing.db")
    assert result["status"] == "MISSING"


def test_event_pipeline_empty_table(tmp_path):
    db = tmp_path / "events.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE market_events (event_date TEXT, ticker TEXT, event_source TEXT)")
    result = audit_event_pipeline(db)
    assert result["status"] == "EMPTY"

