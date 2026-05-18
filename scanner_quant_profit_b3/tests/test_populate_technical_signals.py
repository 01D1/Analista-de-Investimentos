import sqlite3

from src.db.init_db import init_database
from src.scanners.populate_technical_signals import main, run
from tests.technical_fixtures import sample_price_df


def test_populate_technical_signals_persists_history(tmp_path):
    db = tmp_path / "technical_pop.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        sample_price_df(90).to_sql("cotahist_daily", con, if_exists="append", index=False)
    summary = run(start="2026-01-01", end="2026-03-31", tickers=["PETR4"], dedupe=True, save_db=True, db_path=db)
    assert summary["saved_features_count"] > 0
    assert summary["saved_setups_count"] > 0
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM technical_setup_signals").fetchone()[0] == summary["saved_setups_count"]


def test_populate_technical_signals_main_smoke(monkeypatch):
    monkeypatch.setattr(
        "src.scanners.populate_technical_signals.run",
        lambda **kwargs: {"features_count": 0, "setups_count": 0, "saved_features_count": 0, "saved_setups_count": 0, "diagnostics": [], "csv_paths": {}},
    )
    assert main(["--start", "2026-01-02", "--end", "2026-01-03", "--tickers", "PETR4"]) == 0

