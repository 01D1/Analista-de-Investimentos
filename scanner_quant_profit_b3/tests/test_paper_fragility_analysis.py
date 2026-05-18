import sqlite3

from src.db.init_db import init_database
from src.scanners.paper_fragility_analysis import main, run


def _seed(db):
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO paper_orders (run_id, trade_date, ticker, side, quantity, execution_cost, slippage_cost, order_status, signal_source, metadata_json) VALUES (1, '2026-01-02', 'PETR4', 'CLOSE', 1, 1, 1, 'SIMULATED_FILLED', 'quant', '{\"metadata_trade_pnl\": 10}')")
        con.execute("INSERT INTO paper_equity_curve (run_id, trade_date, equity, exposure, drawdown) VALUES (1, '2026-01-01', 100, 0, 0)")
        con.execute("INSERT INTO paper_equity_curve (run_id, trade_date, equity, exposure, drawdown) VALUES (1, '2026-01-02', 90, 10, -0.1)")
        con.execute("INSERT INTO paper_positions (run_id, trade_date, ticker, quantity, market_value, unrealized_pnl) VALUES (1, '2026-01-02', 'PETR4', 1, 10, -2)")


def test_paper_fragility_analysis_run(tmp_path):
    db = tmp_path / "fragility_cli.db"
    _seed(db)
    summary = run(paper_run_id=1, db_path=db, save_db=True)
    assert summary["saved_run_id"] == 1
    assert summary["total_trades"] == 1


def test_paper_fragility_analysis_main_smoke(monkeypatch):
    monkeypatch.setattr("src.scanners.paper_fragility_analysis.run", lambda **kwargs: {"paper_run_id": 1, "status": "COMPLETED", "total_trades": 1, "total_net_pnl": 1, "fragility_score": 10, "fragility_class": "ROBUSTO", "governance_status": "PAPER_FRAGILITY_OK", "saved_run_id": None, "csv_paths": {}})
    assert main(["--paper-run-id", "1"]) == 0
