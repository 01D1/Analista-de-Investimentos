import pandas as pd

from src.data_quality.data_quality_alerts import build_alerts_from_data_source_audit
from src.data_quality.source_inventory import make_audit_row
from src.data_quality.source_reliability import calculate_source_reliability_score


def test_alerts_for_missing_primary_source():
    df = pd.DataFrame([make_audit_row(source_name="b3_cotahist", source_type="MARKET_DATA", primary_or_secondary="PRIMARY", status="MISSING")])
    alerts = build_alerts_from_data_source_audit(calculate_source_reliability_score(df))
    assert "PRIMARY_SOURCE_UNAVAILABLE" in set(alerts["alert_type"])

