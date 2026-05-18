import sqlite3

from src.db.init_db import init_database
from src.scanners.populate_asset_intelligence_history import main, run
from tests.technical_fixtures import sample_price_df


def test_populate_asset_intelligence_history_persists(tmp_path):
    db = tmp_path / "integrated_pop.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        sample_price_df(20).to_sql("cotahist_daily", con, if_exists="append", index=False)
        con.execute("INSERT INTO technical_feature_snapshots (created_at, trade_date, ticker, technical_score_final, technical_status) VALUES ('2026-01-02', '2026-01-02', 'PETR4', 70, 'TECNICO_PROMISSOR')")
        con.execute("INSERT INTO technical_setup_signals (created_at, trade_date, ticker, setup_type, setup_score, setup_confidence) VALUES ('2026-01-02', '2026-01-02', 'PETR4', 'BREAKOUT_VOLUME', 75, 0.7)")
        con.execute("INSERT INTO historical_backtest_results (run_id, trade_date, ticker, score_final, signal_type, signal_confidence) VALUES (1, '2026-01-02', 'PETR4', 72, 'OBSERVAR', 'MEDIA')")
        con.commit()
    summary = run(start="2026-01-01", end="2026-01-20", tickers=["PETR4"], save_db=True, db_path=db)
    assert summary["saved_snapshots_count"] > 0
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM asset_intelligence_snapshots").fetchone()[0] == summary["saved_snapshots_count"]


def test_populate_asset_intelligence_history_main_smoke(monkeypatch):
    monkeypatch.setattr(
        "src.scanners.populate_asset_intelligence_history.run",
        lambda **kwargs: {"snapshots_count": 0, "saved_snapshots_count": 0, "diagnostics": [], "csv_path": ""},
    )
    assert main(["--start", "2026-01-02", "--end", "2026-01-03", "--tickers", "PETR4"]) == 0

