import pandas as pd

from src.data_quality.source_inventory import make_audit_row
from src.data_quality.source_reliability import calculate_source_reliability_score


def test_reliability_score_ok_source():
    df = pd.DataFrame([make_audit_row(source_name="b3", source_type="MARKET_DATA", primary_or_secondary="PRIMARY", available=True, records_count=100, latest_date="2026-04-30", tickers_count=10, status="OK")])
    scored = calculate_source_reliability_score(df)
    assert scored.iloc[0]["reliability_class"] in {"CONFIAVEL", "ACEITAVEL"}


def test_reliability_missing_source():
    df = pd.DataFrame([make_audit_row(source_name="profit", source_type="REALTIME", primary_or_secondary="PRIMARY", status="MISSING")])
    scored = calculate_source_reliability_score(df)
    assert scored.iloc[0]["reliability_class"] in {"INSUFICIENTE", "INDISPONIVEL"}

