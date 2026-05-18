from src.db.init_db import init_database
from src.scanners.options_walk_forward_analysis import run


def test_options_walk_forward_analysis_insufficient_data(tmp_path):
    db = tmp_path / "db.sqlite"
    init_database(db, verbose=False)
    result = run(start="2026-01-01", end="2026-02-28", underlyings=["PETR4"], save_db=True, db_path=db)
    assert result["summary"]["robustness_class"] == "OPTIONS_WF_DADOS_INSUFICIENTES"
    assert result["governance"]["governance_status"] == "OPTIONS_OOS_BLOCKED_INSUFFICIENT_DATA"
    assert result["run_id"] == 1

