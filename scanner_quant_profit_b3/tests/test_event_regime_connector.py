import sqlite3

from src.db.init_db import init_database
from src.integration.connectors.event_regime_connector import load_latest_event_context, load_latest_regime_context


def test_event_regime_connector_empty_tables(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    events = load_latest_event_context(db, ["PETR4"])
    regimes = load_latest_regime_context(db)
    assert len(events) == 1
    assert events.loc[0, "has_recent_event"] == 0
    assert regimes.empty


def test_event_regime_connector_reads_latest(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO market_events (event_date, ticker, event_type, impact_score)
            VALUES ('2026-01-02', 'PETR4', 'FATO_RELEVANTE', -0.4)
            """
        )
        con.execute(
            """
            INSERT INTO event_coverage_runs (created_at, coverage_quality)
            VALUES ('2026-01-02T10:00:00', 'COBERTURA_MEDIA')
            """
        )
        con.execute(
            """
            INSERT INTO market_regime_daily (trade_date, primary_regime, trend_regime, volatility_regime, liquidity_regime, risk_regime)
            VALUES ('2026-01-02', 'LATERAL', 'LATERAL', 'NORMAL', 'LIQUIDEZ_FORTE', 'RISCO_CONTROLADO')
            """
        )
        con.commit()

    events = load_latest_event_context(db, ["PETR4"])
    regime = load_latest_regime_context(db)
    assert events.loc[0, "event_type"] == "FATO_RELEVANTE"
    assert events.loc[0, "event_governance_status"] == "EVENT_COVERAGE_OK"
    assert regime.loc[0, "primary_regime"] == "LATERAL"
