import sqlite3

from src.db.init_db import init_database
from src.signals.signal_coverage import analyze_signal_coverage, generate_signal_coverage_report, summarize_signal_coverage_by_regime


def test_analyze_signal_coverage_by_source_and_regime(tmp_path):
    db = tmp_path / "coverage.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            "INSERT INTO historical_backtest_results (run_id, trade_date, ticker, score_final, signal_type) VALUES (1, '2026-01-02', 'PETR4', 70, 'OBSERVAR')"
        )
        con.execute(
            "INSERT INTO technical_setup_signals (created_at, trade_date, ticker, setup_type, setup_score) VALUES ('2026-01-02', '2026-01-02', 'PETR4', 'BREAKOUT_VOLUME', 75)"
        )
        con.execute(
            "INSERT INTO asset_intelligence_snapshots (created_at, trade_date, ticker, integrated_score, integrated_status) VALUES ('2026-01-02', '2026-01-02', 'PETR4', 55, 'APENAS_MONITORAR')"
        )
        con.execute(
            "INSERT INTO market_regime_daily (trade_date, primary_regime, trend_regime) VALUES ('2026-01-02', 'LATERAL', 'ALTA_TENDENCIAL')"
        )
        con.commit()
    coverage = analyze_signal_coverage(db, "2026-01-02", "2026-01-02", sources=["quant", "technical", "integrated"])
    assert set(coverage["signal_source"]) == {"quant", "technical", "integrated"}
    assert coverage["signals_count"].sum() == 3
    assert "technical" in generate_signal_coverage_report(coverage)

    regimes = coverage
    assert not regimes.empty


def test_summarize_signal_coverage_by_regime():
    import pandas as pd

    signals = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "signal_source": ["quant"]})
    regimes = pd.DataFrame({"trade_date": ["2026-01-02"], "primary_regime": ["LATERAL"]})
    summary = summarize_signal_coverage_by_regime(signals, regimes)
    assert summary.loc[0, "regime_value"] == "LATERAL"

