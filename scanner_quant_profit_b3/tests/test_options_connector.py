import sqlite3

from src.db.init_db import init_database
from src.integration.connectors.options_connector import load_latest_option_candidates, load_latest_option_walk_forward_status


def test_options_connector_missing_db():
    df = load_latest_option_candidates("missing.db", ["PETR4"])
    assert df.empty
    assert "best_option_structure_type" in df.columns


def test_options_connector_best_candidate(tmp_path):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)
    with sqlite3.connect(db) as con:
        con.executemany(
            """
            INSERT INTO option_structure_candidates (created_at, structure_type, underlying, maturity_date, structure_score, liquidity_score, explanation, governance_status)
            VALUES ('2026-01-02T10:00:00', ?, 'PETR4', '2026-02-20', ?, ?, ?, ?)
            """,
            [
                ("LONG_CALL", 55, 60, "estrutura apenas em observação", "STRUCTURE_OBSERVATION_ONLY"),
                ("BULL_CALL_SPREAD", 78, 75, "estrutura potencial a estudar", "STRUCTURE_APPROVED_FOR_STUDY"),
            ],
        )
        con.execute(
            """
            INSERT INTO option_walk_forward_runs (started_at, status, structure_type, governance_status, robustness_class)
            VALUES ('2026-01-02T11:00:00', 'SUCCESS', 'LONG_CALL', 'OPTIONS_OOS_OBSERVATION_ONLY', 'OPTIONS_WF_PROMISSOR')
            """
        )
        con.commit()

    candidates = load_latest_option_candidates(db, ["PETR4"])
    wf = load_latest_option_walk_forward_status(db, ["PETR4"])
    assert candidates.loc[0, "best_option_structure_type"] == "BULL_CALL_SPREAD"
    assert candidates.loc[0, "option_structure_score"] == 78
    assert wf.loc[0, "option_oos_governance_status"] == "OPTIONS_OOS_OBSERVATION_ONLY"
