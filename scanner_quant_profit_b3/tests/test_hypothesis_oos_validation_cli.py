import sqlite3

from src.db.init_db import init_database
from src.scanners.hypothesis_oos_validation import main, run


def _seed(db):
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO paper_investigation_runs (
                created_at, base_paper_run_id, base_fragility_run_id, hypotheses_count,
                improved_count, rejected_count, observation_count, best_hypothesis_id,
                best_improvement_score, metadata_json
            ) VALUES ('2026-01-01', 2, 1, 1, 1, 0, 0,
                      'REDUCE_VOLATILITY_EXPOSURE', 70,
                      '{"config": {"start_date": "2026-01-01", "end_date": "2026-03-31"}}')
            """
        )
        con.execute(
            """
            INSERT INTO paper_investigation_results (
                run_id, hypothesis_id, hypothesis_type, target, title, simulated_return,
                simulated_drawdown, simulated_trades, simulated_win_rate,
                simulated_profit_factor, fragility_score_before, fragility_score_after,
                improvement_score, governance_status, conclusion, metadata_json
            ) VALUES (1, 'REDUCE_VOLATILITY_EXPOSURE', 'REDUCE_VOLATILITY_EXPOSURE',
                      'portfolio', 'Reduzir exposicao', 0.1, -0.08, 30, 0.5,
                      1.2, 30, 20, 70, 'INVESTIGATION_APPROVED_FOR_FURTHER_TEST',
                      'INVESTIGATION_IMPROVED', '{}')
            """
        )
        con.commit()


def test_hypothesis_oos_validation_cli_dry_run(tmp_path):
    db = tmp_path / "hyp_cli.db"
    _seed(db)
    summary = run(investigation_run_id=1, hypothesis_id="REDUCE_VOLATILITY_EXPOSURE", db_path=db, dry_run=True)
    assert summary["status"] == "DRY_RUN"
    assert summary["hypothesis_id"] == "REDUCE_VOLATILITY_EXPOSURE"


def test_hypothesis_oos_validation_main_smoke(monkeypatch):
    monkeypatch.setattr(
        "src.scanners.hypothesis_oos_validation.run",
        lambda **kwargs: {
            "hypothesis_id": "REDUCE_VOLATILITY_EXPOSURE",
            "status": "HYPOTHESIS_PROMISING",
            "robustness_class": "HYPOTHESIS_PROMISING",
            "governance_status": "HYPOTHESIS_APPROVED_FOR_MORE_TESTING",
            "windows_count": 1,
            "scenarios_count": 1,
            "positive_improvement_pct": 1,
            "mean_return_delta": 0.1,
            "mean_drawdown_delta": 0.01,
            "mean_fragility_delta": -2,
            "saved_run_id": None,
            "csv_paths": {},
        },
    )
    assert main(["--investigation-run-id", "1", "--hypothesis-id", "REDUCE_VOLATILITY_EXPOSURE"]) == 0
