import pandas as pd

from src.notifications.alert_engine import (
    build_alerts_from_observability,
    build_alerts_from_retention_cleanup,
    build_alerts_from_source_contracts,
    build_alerts_from_event_coverage,
    build_alerts_from_governance,
    build_alerts_from_health,
    build_daily_routine_alerts,
    send_alerts_to_telegram,
)


def test_build_alerts_from_health_missing_source():
    health = pd.DataFrame(
        [
            {"source_name": "news_hunter", "status": "MISSING", "message": "Banco ausente"},
            {"source_name": "csv", "status": "OK", "message": "ok"},
        ]
    )

    alerts = build_alerts_from_health(health)

    assert len(alerts) == 1
    assert alerts.loc[0, "alert_type"] == "SOURCE_MISSING"
    assert alerts.loc[0, "severity"] == "CRITICAL"


def test_build_alerts_from_event_coverage_insufficient():
    alerts = build_alerts_from_event_coverage({"coverage_quality": "COBERTURA_INSUFICIENTE", "signals_with_event_pct": 0.01})

    assert alerts.loc[0, "alert_type"] == "COVERAGE_INSUFFICIENT"


def test_build_alerts_from_governance_blocked():
    alerts = build_alerts_from_governance({"governance_status": "BLOQUEADO_OVERFITTING", "approved": False, "summary_text": "bloqueado"})

    assert alerts.loc[0, "alert_type"] == "GOVERNANCE_BLOCKED"
    assert alerts.loc[0, "severity"] == "CRITICAL"


def test_build_daily_routine_alerts_warning():
    alerts = build_daily_routine_alerts({"status": "SUCCESS_WITH_WARNINGS"})

    assert alerts.loc[0, "alert_type"] == "ROUTINE_WARNING"


def test_build_alerts_from_observability_generates_sla_and_recurring_alerts():
    alerts = build_alerts_from_observability(
        {
            "critical_sources_list": ["news_hunter"],
            "unstable_sources_list": ["csv"],
            "routine_health_status": "CRITICAL",
            "latest_run_at": "2026-05-01",
            "coverage_trend_direction": "PIORANDO",
            "recurring_alerts": [{"alert_type": "SOURCE_STALE", "source": "csv", "occurrences": 3}],
        }
    )

    assert {
        "SOURCE_SLA_CRITICAL",
        "SOURCE_SLA_UNSTABLE",
        "ROUTINE_NOT_RUNNING",
        "COVERAGE_TREND_WORSENING",
        "RECURRING_ALERT",
    }.issubset(set(alerts["alert_type"]))


def test_build_alerts_from_source_contracts_and_retention_cleanup():
    contracts = pd.DataFrame(
        [
            {"source_name": "cvm", "contract_status": "FAIL", "severity": "CRITICAL", "message": "idade"},
            {"source_name": "csv", "contract_status": "WARNING", "severity": "WARNING", "message": "registros"},
        ]
    )
    contract_alerts = build_alerts_from_source_contracts(contracts)
    retention_alerts = build_alerts_from_retention_cleanup({"status": "DRY_RUN", "rows_candidates": 20000, "rows_deleted": 0, "errors_count": 0})

    assert set(contract_alerts["alert_type"]) == {"SOURCE_CONTRACT_FAILED", "SOURCE_CONTRACT_WARNING"}
    assert retention_alerts.loc[0, "alert_type"] == "RETENTION_CANDIDATES_HIGH"


def test_send_alerts_to_telegram_without_config_returns_message(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    alerts = pd.DataFrame([{"severity": "WARNING", "title": "Teste", "message": "msg"}])

    assert send_alerts_to_telegram(alerts) == "Telegram não configurado"
