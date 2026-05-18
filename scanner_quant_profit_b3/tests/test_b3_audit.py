import sqlite3

from src.data_quality.b3_audit import audit_b3_cotahist, compare_b3_raw_vs_db


def test_b3_without_data(tmp_path):
    result = audit_b3_cotahist(tmp_path / "raw", tmp_path / "processed", tmp_path / "db.sqlite")
    assert result["status"] == "MISSING"


def test_b3_raw_vs_empty_db_warning():
    comparison = compare_b3_raw_vs_db({"files_count": 1, "latest_year": "2026"}, {"records_count": 0, "options_count": 0})
    assert comparison["status"] == "WARNING"


def test_b3_with_db_data(tmp_path):
    db = tmp_path / "db.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE cotahist_daily (trade_date TEXT, ticker TEXT, market_type TEXT, option_type TEXT)")
        con.execute("INSERT INTO cotahist_daily VALUES ('2026-04-30', 'PETR4', 'VISTA', NULL)")
    result = audit_b3_cotahist(tmp_path / "raw", tmp_path / "processed", db)
    assert result["records_count"] == 1
    assert result["tickers_count"] == 1

