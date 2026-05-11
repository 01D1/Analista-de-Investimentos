import sqlite3

from src.db.init_db import init_database
from src.ops.data_retention import estimate_rows_to_cleanup, run_retention_cleanup


def _policy(archive_dir):
    return {
        "retention": {"source_health_checks_days": 10, "market_events_days": 10},
        "archive": {"enabled": True, "dir": str(archive_dir), "format": "csv"},
        "safety": {"never_delete_tables": ["market_events"]},
    }


def test_estimate_rows_to_cleanup_marks_protected(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO source_health_checks (
                checked_at, source_name, status, available, records_count
            ) VALUES ('2026-01-01', 'csv', 'OK', 1, 1)
            """
        )
        con.execute("INSERT INTO market_events (event_date, ticker, event_type) VALUES ('2026-01-01', 'PETR4', 'RESULTADO')")
        con.commit()

    estimates = estimate_rows_to_cleanup(db_path, _policy(tmp_path / "archive"), reference_date="2026-02-01")

    source = estimates[estimates["table_name"] == "source_health_checks"].iloc[0]
    protected = estimates[estimates["table_name"] == "market_events"].iloc[0]
    assert source["rows_to_delete"] == 1
    assert bool(source["can_delete"]) is True
    assert bool(protected["protected"]) is True


def test_retention_dry_run_does_not_delete(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO source_health_checks (checked_at, source_name, status) VALUES ('2026-01-01', 'csv', 'OK')")
        con.commit()

    summary, _ = run_retention_cleanup(db_path, _policy(tmp_path / "archive"), dry_run=True, reference_date="2026-02-01")
    with sqlite3.connect(db_path) as con:
        remaining = con.execute("SELECT COUNT(*) FROM source_health_checks").fetchone()[0]

    assert summary["rows_candidates"] == 1
    assert summary["rows_deleted"] == 0
    assert remaining == 1


def test_retention_execute_requires_confirm(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO source_health_checks (checked_at, source_name, status) VALUES ('2026-01-01', 'csv', 'OK')")
        con.commit()

    summary, _ = run_retention_cleanup(db_path, _policy(tmp_path / "archive"), dry_run=False, confirm=False, reference_date="2026-02-01")
    with sqlite3.connect(db_path) as con:
        remaining = con.execute("SELECT COUNT(*) FROM source_health_checks").fetchone()[0]

    assert summary["dry_run"] == 1
    assert remaining == 1


def test_retention_execute_with_confirm_archives_and_deletes(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    archive_dir = tmp_path / "archive"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO source_health_checks (checked_at, source_name, status) VALUES ('2026-01-01', 'csv', 'OK')")
        con.commit()

    summary, _ = run_retention_cleanup(db_path, _policy(archive_dir), dry_run=False, confirm=True, reference_date="2026-02-01")
    with sqlite3.connect(db_path) as con:
        remaining = con.execute("SELECT COUNT(*) FROM source_health_checks").fetchone()[0]

    assert summary["rows_archived"] == 1
    assert summary["rows_deleted"] == 1
    assert remaining == 0
    assert list(archive_dir.glob("source_health_checks_*.csv"))


def test_retention_handles_resolved_alerts_special_policy(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    archive_dir = tmp_path / "archive"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO operational_alerts (
                created_at, alert_type, severity, title, resolved
            ) VALUES ('2026-01-01', 'SOURCE_STALE', 'WARNING', 'stale', 1)
            """
        )
        con.commit()
    policy = {
        "retention": {"resolved_alerts_days": 10},
        "archive": {"enabled": True, "dir": str(archive_dir), "format": "csv"},
        "safety": {"never_delete_tables": []},
    }

    summary, details = run_retention_cleanup(db_path, policy, dry_run=False, confirm=True, reference_date="2026-02-01")

    assert summary["rows_deleted"] == 1
    assert details.loc[0, "table_name"] == "resolved_alerts"


def test_retention_handles_event_coverage_by_regime_special_policy(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO event_coverage_runs (
                id, created_at, signals_count, signals_with_event_pct
            ) VALUES (1, '2026-01-01', 10, 0.1)
            """
        )
        con.execute(
            """
            INSERT INTO event_coverage_by_regime (
                coverage_run_id, regime_type, regime_value, signals_count
            ) VALUES (1, 'primary_regime', 'LATERAL', 10)
            """
        )
        con.commit()
    policy = {
        "retention": {"event_coverage_by_regime_days": 10},
        "archive": {"enabled": False, "dir": str(tmp_path / "archive"), "format": "csv"},
        "safety": {"never_delete_tables": []},
    }

    summary, _ = run_retention_cleanup(db_path, policy, dry_run=False, confirm=True, reference_date="2026-02-01")

    assert summary["rows_deleted"] == 1
