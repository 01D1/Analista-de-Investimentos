import sqlite3

from src.db.init_db import init_database
from src.scanners.options_history_builder import run


def test_options_history_builder_handles_no_data(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    result = run(start="2026-01-02", end="2026-01-03", underlyings=["PETR4"], db_path=db)
    assert result["snapshots"].empty
    assert result["coverage"].loc[0, "coverage_status"] == "SEM_DADOS"


def test_options_history_builder_with_synthetic_cotahist(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO cotahist_daily (
                trade_date, ticker, market_type, open, high, low, close, best_bid,
                best_ask, trades, quantity, volume, strike, option_type,
                expiration_date, source_year
            ) VALUES ('2026-01-02', 'PETRA300', '070', 1, 1.2, 0.9, 1.1,
                      1.0, 1.2, 100, 10000, 100000, 30, 'CALL',
                      '2026-02-20', 2026)
            """
        )
        con.execute(
            """
            INSERT INTO cotahist_daily (
                trade_date, ticker, market_type, open, high, low, close,
                trades, quantity, volume, source_year
            ) VALUES ('2026-01-02', 'PETR4', '010', 31, 32, 30, 31,
                      1000, 100000, 10000000, 2026)
            """
        )
        con.commit()

    result = run(start="2026-01-02", end="2026-01-02", underlyings=["PETR4"], save_db=True, db_path=db)
    assert len(result["snapshots"]) == 1
    assert result["saved"] == 1
    assert result["snapshots"].loc[0, "underlying"] == "PETR4"

