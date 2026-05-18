import sqlite3

from src.db.init_db import init_database
from src.scanners.technical_analysis_scanner import run
from tests.technical_fixtures import sample_price_df


def test_technical_analysis_scanner_with_synthetic_db(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    prices = sample_price_df()
    with sqlite3.connect(db_path) as con:
        prices.to_sql("cotahist_daily", con, if_exists="append", index=False)
    result = run(
        start="2026-01-01",
        end="2026-03-31",
        tickers=["PETR4"],
        save_db=True,
        write_csv=False,
        with_backtest=True,
        db_path=db_path,
    )
    assert not result["features"].empty
    assert not result["setups"].empty
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM technical_feature_snapshots").fetchone()[0] > 0
        assert con.execute("SELECT COUNT(*) FROM technical_setup_signals").fetchone()[0] > 0

