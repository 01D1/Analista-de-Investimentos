from src.ops.retention_policy import (
    get_archive_settings,
    get_table_retention_days,
    is_protected_table,
    load_retention_policy,
    validate_retention_policy,
)


def test_load_default_retention_policy_when_missing(tmp_path):
    policy = load_retention_policy(tmp_path / "missing.yaml")

    assert get_table_retention_days(policy, "source_health_checks") == 180
    assert get_archive_settings(policy)["enabled"] is True
    assert is_protected_table(policy, "market_events") is True


def test_validate_retention_policy_rejects_negative_and_protected():
    policy = {
        "retention": {"market_events_days": 10, "source_health_checks_days": -1},
        "safety": {"never_delete_tables": ["market_events"]},
    }

    errors = validate_retention_policy(policy)

    assert any("negativa" in error for error in errors)
    assert any("protegida" in error for error in errors)
