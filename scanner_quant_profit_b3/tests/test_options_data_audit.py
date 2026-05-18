import sqlite3

from src.data_quality.options_data_audit import audit_options_data


def test_options_without_snapshots(tmp_path):
    db = tmp_path / "db.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE options_chain_snapshots (trade_date TEXT, captured_at TEXT, underlying TEXT, maturity_date TEXT, bid REAL, ask REAL, volume REAL, trades REAL)")
    result = audit_options_data(db)
    assert result["historical_coverage_status"] == "SEM_DADOS"
    assert result["status"] == "EMPTY"

