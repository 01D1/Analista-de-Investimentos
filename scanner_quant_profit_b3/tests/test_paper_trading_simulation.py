import sqlite3

import numpy as np
import pandas as pd

from src.db.init_db import init_database
from src.scanners.paper_trading_simulation import main, run


def _seed_db(db):
    init_database(db, verbose=False)
    dates = pd.date_range("2026-01-01", periods=10).astype(str)
    with sqlite3.connect(db) as con:
        for i, date in enumerate(dates):
            con.execute(
                "INSERT INTO cotahist_daily (trade_date, ticker, market_type, open, high, low, close, volume, trades) VALUES (?, 'PETR4', '010', ?, ?, ?, ?, ?, ?)",
                (date, 20 + i, 21 + i, 19 + i, 20 + i, 100_000, 100),
            )
        con.execute(
            """
            INSERT INTO asset_intelligence_snapshots (
                created_at, trade_date, ticker, integrated_status, integrated_governance_status, data_quality_score
            ) VALUES ('2026-01-02T10:00:00', '2026-01-02', 'PETR4', 'ASSIMETRIA_A_INVESTIGAR', 'INTEGRATED_APPROVED_FOR_STUDY', 80)
            """
        )
        con.execute(
            """
            INSERT INTO risk_snapshots (
                created_at, trade_date, ticker, price, position_value, ensemble_vol, volatility_regime,
                parametric_var_95, historical_var_95, expected_shortfall_95, recommended_size,
                recommended_position_value, limiting_factor, risk_status, explanation, metadata_json
            ) VALUES ('2026-01-02T10:00:00', '2026-01-02', 'PETR4', 20, 200, 0.2, 'VOL_NORMAL', 5, 5, 8, 10, 200, 'FIXED_RISK', 'RISK_OK', 'ok', '{}')
            """
        )


def test_paper_trading_simulation_run_dry_and_save(tmp_path):
    db = tmp_path / "paper_cli.db"
    _seed_db(db)
    summary = run(start="2026-01-01", end="2026-01-10", db_path=db, save_db=True)
    assert summary["signals_count"] == 1
    assert summary["saved_run_id"] == 1


def test_paper_trading_simulation_run_advanced(tmp_path):
    db = tmp_path / "paper_cli_advanced.db"
    _seed_db(db)
    summary = run(
        start="2026-01-01",
        end="2026-01-10",
        db_path=db,
        save_db=True,
        exit_mode="advanced",
        stop_loss_pct=0.03,
        take_profit_pct=0.06,
        trailing_stop_pct=0.04,
        enable_rebalancing=True,
        save_attribution=True,
    )
    assert summary["saved_run_id"] == 1
    assert "exit_events_count" in summary


def test_paper_trading_simulation_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.paper_trading_simulation.run", lambda **kwargs: {"status": "INSUFFICIENT_DATA", "signals_count": 0, "orders_count": 0, "trades_count": 0, "capital_final": 100000, "governance_status": "PAPER_BLOCKED_LOW_SAMPLE", "exit_events_count": 0, "rebalance_events_count": 0, "saved_run_id": None, "csv_paths": {}})
    assert main(["--dry-run"]) == 0
