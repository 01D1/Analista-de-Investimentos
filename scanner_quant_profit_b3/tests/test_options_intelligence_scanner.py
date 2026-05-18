import sqlite3

from src.db.init_db import init_database
from src.scanners.options_intelligence_scanner import run


def test_options_intelligence_scanner_with_synthetic_data(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO cotahist_daily (
                trade_date, ticker, market_type, close, trades, volume
            ) VALUES ('2026-05-01', 'PETR4', '010', 31, 1000, 10000000)
            """
        )
        for ticker, opt_type, strike, close in [
            ("PETRA100", "CALL", 30, 1.5),
            ("PETRB100", "CALL", 32, 0.7),
            ("PETRM100", "PUT", 32, 1.3),
            ("PETRN100", "PUT", 30, 0.6),
        ]:
            con.execute(
                """
                INSERT INTO cotahist_daily (
                    trade_date, ticker, market_type, close, best_bid, best_ask,
                    trades, quantity, volume, strike, option_type, expiration_date
                ) VALUES ('2026-05-01', ?, '070', ?, ?, ?, 100, 10000, 200000, ?, ?, '2026-06-01')
                """,
                (ticker, close, close - 0.05, close + 0.05, strike, opt_type),
            )
        con.commit()

    result = run(underlyings=["PETR4"], min_volume=1, min_trades=1, max_spread_pct=20, min_dte=1, max_dte=90, save_db=True, write_csv=False, dry_run=False, db_path=db_path)

    assert len(result["chain"]) == 4
    assert not result["structures"].empty
    assert result["run_id"] == 1
