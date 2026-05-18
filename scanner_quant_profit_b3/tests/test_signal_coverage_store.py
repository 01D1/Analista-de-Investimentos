from src.db.init_db import init_database
from src.signals.signal_coverage import analyze_signal_coverage
from src.signals.signal_coverage_requirements import evaluate_signal_coverage_requirements
from src.signals.signal_coverage_store import load_latest_signal_coverage, load_signal_coverage_history, save_signal_coverage_run


def test_signal_coverage_store_roundtrip(tmp_path):
    db = tmp_path / "store.db"
    init_database(db, verbose=False)
    coverage = evaluate_signal_coverage_requirements(analyze_signal_coverage(db, "2026-01-02", "2026-01-31", sources=["quant"]))
    run_id = save_signal_coverage_run(db, coverage, "2026-01-02", "2026-01-31", ["quant"])
    latest = load_latest_signal_coverage(db)
    history = load_signal_coverage_history(db)
    assert run_id == 1
    assert latest.loc[0, "signal_source"] == "quant"
    assert history.loc[0, "coverage_status"] == "COVERAGE_INSUFFICIENT"

