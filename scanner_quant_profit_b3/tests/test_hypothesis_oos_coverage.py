import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.paper.hypothesis_oos_coverage import (
    compare_coverage_before_after,
    diagnose_oos_coverage,
    filter_scenarios_by_coverage,
    load_expanded_paper_signals,
    summarize_coverage,
    summarize_source_coverage_requirements,
)


def test_diagnose_oos_coverage_and_filter():
    signals = pd.DataFrame({"trade_date": ["2026-02-05"], "ticker": ["PETR4"], "signal_source": ["quant"]})
    prices = pd.DataFrame({"trade_date": pd.date_range("2026-02-01", periods=10).astype(str), "ticker": ["PETR4"] * 10, "close": range(10)})
    scenarios = pd.DataFrame({"scenario_name": ["BASE_COST", "TECHNICAL_ONLY"], "signal_source": ["quant", "technical"], "regime_filter": ["", ""]})
    coverage = diagnose_oos_coverage(signals, prices, None, scenarios, "2026-01-01", "2026-03-31", train_months=1, test_months=1)
    summary = summarize_coverage(coverage)
    assert summary["useful_cells"] >= 1
    filtered = filter_scenarios_by_coverage(scenarios, coverage)
    assert "BASE_COST" in filtered["scenario_name"].tolist()


def test_compare_coverage_before_after():
    before = pd.DataFrame({"useful_cell": [False, True], "signal_source": ["technical", "quant"], "regime_filter": ["", ""]})
    after = pd.DataFrame({"useful_cell": [True, True], "signal_source": ["technical", "quant"], "regime_filter": ["", ""]})
    comparison = compare_coverage_before_after(before, after)
    assert comparison["useful_cells_delta"] == 1


def test_load_expanded_paper_signals_from_technical_backtest(tmp_path):
    db = tmp_path / "coverage.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO technical_backtest_results (
                run_id, trade_date, ticker, setup_type, technical_score_final,
                technical_status, future_return_1d, future_return_3d,
                future_return_5d, future_return_10d, hit_1d, hit_3d,
                hit_5d, hit_10d, metadata_json
            ) VALUES (1, '2026-02-05', 'PETR4', 'BREAKOUT', 70,
                      'TECNICO_PROMISSOR', 0, 0, 0, 0, 0, 0, 0, 0, '{}')
            """
        )
        con.commit()
    signals = load_expanded_paper_signals(db, ["technical"], "2026-02-01", "2026-02-28")
    assert "technical" in signals["signal_source"].tolist()


def test_summarize_source_coverage_requirements_excludes_low_sample():
    coverage = pd.DataFrame(
        {
            "useful_cell": [True, True, False],
            "signal_source": ["quant", "quant", "technical"],
            "signals_count": [20, 20, 1],
            "tickers_count": [2, 2, 1],
            "regime_filter": ["", "", ""],
        }
    )
    summary = summarize_source_coverage_requirements(coverage, min_useful_coverage_pct=0.5, min_signals_per_source=30)
    assert "quant" in summary["passed_sources"]
    assert "technical" in summary["excluded_sources"]
