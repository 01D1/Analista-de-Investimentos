import sqlite3

from src.db.init_db import init_database
from src.scanners.paper_investigation import main, run


def _seed(db):
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO paper_simulation_runs (
                started_at, finished_at, status, start_date, end_date, capital_initial,
                capital_final, total_return, sharpe, sortino, max_drawdown, trades_count,
                win_rate, profit_factor, governance_status, metadata_json
            ) VALUES ('2026-01-01', '2026-01-10', 'COMPLETED', '2026-01-01', '2026-01-10',
                      100000, 99500, -0.005, 0, 0, -0.09, 10, 0.4, 0.8,
                      'PAPER_BLOCKED_NEGATIVE_RETURN', '{"signal_source": "quant"}')
            """
        )
        con.execute(
            """
            INSERT INTO paper_fragility_runs (
                created_at, source_run_id, status, total_trades, total_net_pnl,
                fragility_score, fragility_class, governance_status, metadata_json
            ) VALUES ('2026-01-10', 1, 'COMPLETED', 10, -100, 80, 'CRITICO',
                      'PAPER_FRAGILITY_BLOCKED_SIGNAL_SOURCE', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO paper_fragility_by_asset (
                run_id, ticker, trades_count, net_pnl, win_rate, contribution_pct,
                cost_drag, drawdown_contribution, fragility_score, fragility_class, metadata_json
            ) VALUES (1, 'ITUB4', 10, -100, 0.2, -1, 50, 0.1, 80, 'CRITICO', '{}')
            """
        )
        con.commit()


def test_paper_investigation_run_dry_run(tmp_path):
    db = tmp_path / "investigation_cli.db"
    _seed(db)
    summary = run(paper_run_id=1, fragility_run_id=1, db_path=db, dry_run=True)
    assert summary["hypotheses_count"] >= 1
    assert summary["saved_run_id"] is None


def test_paper_investigation_main_smoke(monkeypatch):
    monkeypatch.setattr(
        "src.scanners.paper_investigation.run",
        lambda **kwargs: {
            "status": "COMPLETED",
            "paper_run_id": 2,
            "fragility_run_id": 1,
            "hypotheses_count": 1,
            "results_count": 1,
            "improved_count": 0,
            "best_hypothesis_id": "EXCLUDE_ASSET_ITUB4",
            "best_improvement_score": 10,
            "saved_run_id": None,
            "csv_paths": {},
        },
    )
    assert main(["--paper-run-id", "2", "--fragility-run-id", "1"]) == 0
