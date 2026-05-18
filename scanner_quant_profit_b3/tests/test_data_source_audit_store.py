import pandas as pd

from src.data_quality.data_source_audit_store import (
    load_latest_data_source_audit,
    save_data_source_audit_run,
    save_traceability_records,
)
from src.data_quality.source_inventory import make_audit_row
from src.data_quality.source_reliability import calculate_source_reliability_score


def test_save_and_load_data_source_audit(tmp_path):
    db = tmp_path / "audit.db"
    df = calculate_source_reliability_score(
        pd.DataFrame([make_audit_row(source_name="b3_cotahist", source_type="MARKET_DATA", primary_or_secondary="PRIMARY", status="OK", available=True, records_count=1)])
    )
    run_id = save_data_source_audit_run(db, {"overall_status": "OK", "sources_checked": 1, "ok_count": 1}, df)
    loaded = load_latest_data_source_audit(db)
    assert run_id == 1
    assert loaded["results"].iloc[0]["source_name"] == "b3_cotahist"


def test_save_traceability_records(tmp_path):
    db = tmp_path / "trace.db"
    rows = pd.DataFrame(
        [
            {
                "created_at": "2026-05-12",
                "ticker": "PETR4",
                "data_domain": "MARKET_DATA",
                "source_name": "b3",
                "source_type": "PRIMARY",
                "source_url_or_path": "data/raw",
                "source_date": "2026-04-30",
                "collected_at": "2026-05-12",
                "record_count": 1,
                "checksum": "",
                "metadata_json": "{}",
            }
        ]
    )
    assert save_traceability_records(db, rows) == 1

