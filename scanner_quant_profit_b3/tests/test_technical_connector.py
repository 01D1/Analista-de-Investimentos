import sqlite3

from src.db.init_db import init_database
from src.integration.connectors.technical_connector import load_latest_technical_signals, load_latest_technical_walk_forward_status


def test_technical_connector_missing_db(tmp_path):
    df = load_latest_technical_signals(tmp_path / "missing.db", ["PETR4"])
    assert df.empty
    assert "technical_score_final" in df.columns


def test_technical_connector_latest_signal(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO technical_feature_snapshots (created_at, trade_date, ticker, technical_score_final, technical_status)
            VALUES ('2026-01-02T10:00:00', '2026-01-02', 'PETR4', 78, 'TECNICO_PROMISSOR')
            """
        )
        con.execute(
            """
            INSERT INTO technical_setup_signals (created_at, trade_date, ticker, setup_type, setup_score, setup_confidence, technical_status, governance_status, explanation)
            VALUES ('2026-01-02T10:00:00', '2026-01-02', 'PETR4', 'BREAKOUT_VOLUME', 82, 0.8, 'TECNICO_PROMISSOR', 'TECH_OBSERVATION_ONLY', 'setup técnico em estudo')
            """
        )
        con.execute(
            """
            INSERT INTO technical_walk_forward_runs (started_at, status, robustness_class, governance_status, positive_windows_pct)
            VALUES ('2026-01-02T11:00:00', 'SUCCESS', 'TECH_WF_PROMISSOR', 'TECH_OOS_OBSERVATION_ONLY', 60)
            """
        )
        con.commit()

    signals = load_latest_technical_signals(db, ["PETR4"])
    wf = load_latest_technical_walk_forward_status(db, ["PETR4"])
    assert signals.loc[0, "top_technical_setup"] == "BREAKOUT_VOLUME"
    assert signals.loc[0, "technical_score_final"] == 78
    assert wf.loc[0, "technical_oos_status"] == "TECH_OOS_OBSERVATION_ONLY"
