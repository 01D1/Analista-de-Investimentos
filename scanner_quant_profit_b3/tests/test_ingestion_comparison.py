import pandas as pd

from src.data_quality.ingestion_comparison import compare_reliability_before_after


def test_compare_reliability_before_after():
    before = pd.DataFrame([{"source_name": "b3", "reliability_score": 40, "status": "MISSING", "records_count": 0, "latest_date": ""}])
    after = pd.DataFrame([{"source_name": "b3", "reliability_score": 80, "status": "OK", "records_count": 10, "latest_date": "2026-04-30"}])
    comp = compare_reliability_before_after(before, after)
    assert comp.iloc[0]["score_delta"] == 40
    assert bool(comp.iloc[0]["status_improved"]) is True
