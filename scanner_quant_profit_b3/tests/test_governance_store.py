from src.db.init_db import init_database
from src.quant.governance import BLOQUEADO_OVERFITTING, evaluate_candidate_strategy
from src.quant.governance_store import (
    load_governance_reviews,
    load_latest_governance_review,
    save_governance_review,
    summarize_governance_reviews,
)


def test_governance_store_saves_and_loads_review(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    review = evaluate_candidate_strategy(
        {
            "windows_count": 3,
            "total_signals": 300,
            "positive_windows_pct": 33.3,
            "mean_test_net_return": -0.3,
            "mean_hit_rate": 0.46,
            "avg_top_3_concentration_pct": 36.7,
            "overfitting_alert": True,
            "robustness_class": "OVERFIT_PROVAVEL",
        }
    )
    review.update({"source_type": "filter_walk_forward", "source_run_id": 2, "candidate_name": "filtros_v1"})

    review_id = save_governance_review(db_path, review)
    loaded = load_governance_reviews(db_path)
    latest = load_latest_governance_review(db_path, source_type="filter_walk_forward")
    summary = summarize_governance_reviews(db_path)

    assert review_id == 1
    assert loaded.loc[0, "governance_status"] == BLOQUEADO_OVERFITTING
    assert latest.loc[0, "candidate_name"] == "filtros_v1"
    assert summary.loc[summary["governance_status"] == BLOQUEADO_OVERFITTING, "reviews"].iloc[0] == 1


def test_governance_store_handles_missing_database(tmp_path):
    db_path = tmp_path / "missing.db"

    assert load_governance_reviews(db_path).empty
    assert load_latest_governance_review(db_path).empty
    assert summarize_governance_reviews(db_path).empty
