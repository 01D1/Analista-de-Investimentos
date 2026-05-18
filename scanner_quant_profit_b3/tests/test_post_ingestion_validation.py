import sqlite3

from src.data_quality.post_ingestion_validation import validate_b3_after_ingestion, validate_options_after_ingestion


def test_validate_b3_without_data(tmp_path):
    result = validate_b3_after_ingestion(tmp_path / "missing.db")
    assert result["validation_status"] == "FAILED"


def test_validate_options_without_snapshots(tmp_path):
    db = tmp_path / "options.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE options_chain_snapshots (trade_date TEXT, captured_at TEXT, underlying TEXT, maturity_date TEXT, strike REAL, bid REAL, ask REAL, volume REAL, trades REAL)")
    result = validate_options_after_ingestion(db, ["PETR4"])
    assert result["validation_status"] == "FAILED"

