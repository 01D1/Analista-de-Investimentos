import pandas as pd

from src.context.source_quality_contracts import evaluate_source_contracts, generate_contract_report


def test_source_contract_passes():
    health = pd.DataFrame([{"checked_at": "2026-05-01", "source_name": "news_hunter", "status": "OK", "age_days": 1, "records_count": 30}])
    coverage = pd.DataFrame([{"created_at": "2026-05-01", "sources": "news_hunter", "signals_with_event_pct": 0.1}])
    contracts = {"sources": {"news_hunter": {"required": True, "max_age_days": 3, "min_records": 20, "min_coverage_pct": 5, "severity_if_fail": "WARNING"}}}

    result = evaluate_source_contracts(health, coverage, contracts)

    assert result.loc[0, "contract_status"] == "PASS"


def test_source_contract_fails_by_age_and_records():
    health = pd.DataFrame([{"checked_at": "2026-05-01", "source_name": "cvm", "status": "OK", "age_days": 40, "records_count": 1}])
    contracts = {"sources": {"cvm": {"required": True, "max_age_days": 30, "min_records": 5, "severity_if_fail": "CRITICAL"}}}

    result = evaluate_source_contracts(health, None, contracts)
    report = generate_contract_report(result)

    assert result.loc[0, "contract_status"] == "FAIL"
    assert result.loc[0, "checks_failed"] == 2
    assert "cvm" in report


def test_optional_source_without_health_is_not_applicable():
    contracts = {"sources": {"csv": {"required": False, "min_records": 1, "severity_if_fail": "INFO"}}}

    result = evaluate_source_contracts(pd.DataFrame(), None, contracts)

    assert result.loc[0, "contract_status"] == "NOT_APPLICABLE"
