import sqlite3

from src.db.init_db import init_database
from src.scanners.options_structure_backtest import run


def _insert_snapshot(con, date, price, dte):
    con.execute(
        """
        INSERT INTO options_chain_snapshots (
            trade_date, captured_at, option_ticker, underlying, option_type, strike,
            maturity_date, days_to_maturity, last_price, bid, ask, spread_pct,
            volume, trades, financial_volume, underlying_price, moneyness_class,
            liquidity_score, risk_score, metadata_json
        ) VALUES (?, ?, 'PETRA300', 'PETR4', 'CALL', 30,
                  '2026-02-20', ?, ?, ?, ?, 5,
                  10000, 100, 100000, 31, 'ATM', 80, 70, '{}')
        """,
        (date, date + "T18:00:00", dte, price, price - 0.05, price + 0.05),
    )


def test_options_structure_backtest_insufficient_data(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    result = run(start="2026-01-02", end="2026-01-10", underlyings=["PETR4"], db_path=db)
    assert result["summary"]["status"] == "INSUFFICIENT_DATA"
    assert result["governance"]["governance_status"] == "OPTIONS_BACKTEST_BLOQUEADO_DADOS"


def test_options_structure_backtest_with_synthetic_snapshots(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        _insert_snapshot(con, "2026-01-02", 1.0, 40)
        _insert_snapshot(con, "2026-01-07", 1.7, 35)
        con.commit()

    result = run(start="2026-01-02", end="2026-01-10", underlyings=["PETR4"], structure="LONG_CALL", save_db=True, db_path=db)
    assert result["summary"]["total_trades"] >= 1
    assert result["summary"]["completed_count"] >= 1
    assert result["run_id"] == 1

