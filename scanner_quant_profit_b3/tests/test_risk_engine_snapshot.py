import sqlite3

import numpy as np
import pandas as pd

from src.scanners.risk_engine_snapshot import run


def _seed_prices(db):
    dates = pd.date_range("2026-01-01", periods=90)
    close = 20 + np.linspace(0, 3, 90) + np.sin(np.arange(90)) * 0.2
    rows = [
        (str(date.date()), "PETR4", float(c * 0.99), float(c * 1.02), float(c * 0.98), float(c), 100_000.0, 100)
        for date, c in zip(dates, close)
    ]
    with sqlite3.connect(db) as con:
        con.execute(
            "CREATE TABLE cotahist_daily (trade_date TEXT, ticker TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL, trades REAL)"
        )
        con.executemany("INSERT INTO cotahist_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)


def test_risk_engine_snapshot_cli_run_with_synthetic_data(tmp_path):
    db = tmp_path / "risk_cli.db"
    _seed_prices(db)
    summary = run(["PETR4"], capital=100_000, risk_pct=0.005, save_db=True, db_path=db)
    assert summary["tickers_analyzed"] == 1
    assert summary["saved"]["risk"] == 1
    assert not summary["outputs"]["risk"].empty


def test_risk_engine_snapshot_handles_missing_data(tmp_path):
    summary = run(["PETR4"], db_path=tmp_path / "missing.db")
    assert summary["tickers_analyzed"] == 0
    assert summary["diagnostics"]
