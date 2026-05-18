import sqlite3

from src.db.init_db import init_database
from src.integration.connectors.quant_connector import load_latest_quant_signals, load_quant_governance_by_ticker


def test_quant_connector_empty_source(tmp_path):
    df = load_latest_quant_signals(tmp_path / "missing.db", ["PETR4"])
    assert df.empty
    assert "quant_score" in df.columns


def test_quant_connector_latest_signal_and_governance(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.execute(
            """
            INSERT INTO historical_backtest_results (run_id, trade_date, ticker, score_final, signal_type, signal_confidence, explanation)
            VALUES (1, '2026-01-02', 'PETR4', 81, 'SINAL_QUANT_EM_ESTUDO', 'ALTA', 'sinal quantitativo analítico')
            """
        )
        con.execute(
            """
            INSERT INTO governance_reviews (created_at, source_type, candidate_name, governance_status)
            VALUES ('2026-01-02T10:00:00', 'quant', 'filtro', 'GOVERNANCE_OBSERVATION_ONLY')
            """
        )
        con.commit()

    signals = load_latest_quant_signals(db, ["PETR4"])
    gov = load_quant_governance_by_ticker(db, ["PETR4"])
    assert signals.loc[0, "quant_score"] == 81
    assert gov.loc[0, "quant_governance_status"] == "GOVERNANCE_OBSERVATION_ONLY"
