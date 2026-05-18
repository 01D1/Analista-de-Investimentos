import pandas as pd

from src.data_quality.source_inventory import build_traceability_records, make_audit_row


def test_make_audit_row_schema():
    row = make_audit_row(
        source_name="b3_cotahist",
        source_type="MARKET_DATA",
        primary_or_secondary="PRIMARY",
        available=True,
        records_count=10,
        latest_date="2026-04-30",
        tickers_count=2,
        status="OK",
    )
    assert row["source_name"] == "b3_cotahist"
    assert row["available"] is True
    assert row["records_count"] == 10


def test_traceability_records_from_audit():
    df = pd.DataFrame(
        [
            make_audit_row(
                source_name="valuation_pipeline",
                source_type="VALUATION",
                primary_or_secondary="DERIVED",
                metadata={"tickers": ["PETR4", "VALE3"]},
            )
        ]
    )
    trace = build_traceability_records(df)
    assert set(trace["ticker"]) == {"PETR4", "VALE3"}

