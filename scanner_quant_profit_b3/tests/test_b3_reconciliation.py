import sqlite3

from src.data_quality.b3_reconciliation import compare_b3_raw_vs_sqlite, summarize_b3_raw_files, summarize_b3_sqlite


def test_b3_raw_present_db_empty(tmp_path):
    (tmp_path / "COTAHIST_A2026.ZIP").write_bytes(b"zip")
    raw = summarize_b3_raw_files(tmp_path)
    sqlite = summarize_b3_sqlite(tmp_path / "missing.db")
    result = compare_b3_raw_vs_sqlite(raw, sqlite)
    assert "RAW_PRESENT_DB_EMPTY" in set(result["issue_type"])


def test_b3_raw_newer_than_db(tmp_path):
    (tmp_path / "COTAHIST_A2026.ZIP").write_bytes(b"zip")
    db = tmp_path / "b3.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE cotahist_daily (trade_date TEXT, ticker TEXT, option_type TEXT)")
        con.execute("INSERT INTO cotahist_daily VALUES ('2025-01-02','PETR4',NULL)")
    result = compare_b3_raw_vs_sqlite(summarize_b3_raw_files(tmp_path), summarize_b3_sqlite(db))
    assert {"DB_MISSING_YEAR", "RAW_NEWER_THAN_DB"}.intersection(set(result["issue_type"]))

