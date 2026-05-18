import sqlite3

from src.data_quality.options_reconciliation import compare_options_expectation_vs_available, summarize_options_sources


def test_options_without_snapshots(tmp_path):
    db = tmp_path / "options.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE options_chain_snapshots (trade_date TEXT, captured_at TEXT, underlying TEXT, maturity_date TEXT, strike REAL, bid REAL, ask REAL, volume REAL, trades REAL)")
    summary = summarize_options_sources(db)
    result = compare_options_expectation_vs_available(["PETR4"], summary)
    assert "NO_CHAIN_SNAPSHOTS" in set(result["issue_type"])

