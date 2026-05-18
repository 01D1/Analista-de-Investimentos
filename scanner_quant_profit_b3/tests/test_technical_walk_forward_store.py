import pandas as pd

from src.db.init_db import init_database
from src.technical.technical_walk_forward_store import (
    load_technical_walk_forward_results,
    load_technical_walk_forward_runs,
    save_technical_walk_forward_run,
)


def test_technical_walk_forward_store_roundtrip(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    summary = {
        "started_at": "2026-01-01T10:00:00",
        "finished_at": "2026-01-01T10:01:00",
        "status": "SUCCESS",
        "start_date": "2026-01-01",
        "end_date": "2026-04-30",
        "train_months": 3,
        "test_months": 1,
        "windows_count": 1,
        "positive_windows_pct": 100,
        "mean_test_return": 0.5,
        "mean_test_hit_rate": 60,
        "robustness_class": "TECH_WF_PROMISSOR",
        "governance_status": "TECH_OOS_OBSERVATION_ONLY",
    }
    results = pd.DataFrame({"window_id": [1], "train_start": ["2026-01-01"], "train_end": ["2026-03-31"], "test_start": ["2026-04-01"], "test_end": ["2026-04-30"], "test_signals": [30], "test_mean_return": [0.5]})
    run_id = save_technical_walk_forward_run(db_path, summary, results)
    assert run_id == 1
    assert load_technical_walk_forward_runs(db_path).loc[0, "robustness_class"] == "TECH_WF_PROMISSOR"
    assert load_technical_walk_forward_results(db_path, run_id=1).loc[0, "test_signals"] == 30

