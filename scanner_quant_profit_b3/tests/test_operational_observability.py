import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.scanners.operational_observability import run


def test_operational_observability_run_saves_snapshots(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    now = pd.Timestamp.now().isoformat()
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO source_health_checks (
                checked_at, source_name, status, available, records_count,
                latest_date, age_days, coverage_hint, path, message, metadata_json
            ) VALUES (?, 'csv', 'OK', 1, 10, '2026-05-01', 0, 'ok', 'events.csv', 'ok', '{}')
            """,
            (now,),
        )
        con.execute(
            """
            INSERT INTO event_coverage_runs (
                created_at, start_date, end_date, sources, events_loaded,
                events_after_dedup, tickers_count, signals_count,
                signals_with_event_pct, tickers_with_event_pct, coverage_quality
            ) VALUES (?, '2026-05-01', '2026-05-10', 'csv', 10, 9, 5, 100, 0.12, 0.4, 'COBERTURA_MEDIA')
            """,
            (now,),
        )
        con.execute(
            """
            INSERT INTO daily_routine_runs (
                started_at, finished_at, status, start_date, end_date, sources,
                health_overall_status, event_coverage_quality, events_loaded,
                events_after_dedup, signals_covered_pct, alerts_count
            ) VALUES (?, ?, 'SUCCESS', '2026-05-01', '2026-05-10',
                      'csv', 'OK', 'COBERTURA_MEDIA', 10, 9, 0.12, 0)
            """,
            (now, now),
        )
        con.commit()

    output = run(window_days=30, save_db=True, write_csv=False, db_path=db_path)

    assert output["summary"]["overall_status"] in {"OK", "WARNING"}
    assert not output["source_sla"].empty
    assert output["snapshot_id"] == 1
    with sqlite3.connect(db_path) as con:
        sla_rows = con.execute("SELECT COUNT(*) FROM source_sla_snapshots").fetchone()[0]
        obs_rows = con.execute("SELECT COUNT(*) FROM operational_observability_snapshots").fetchone()[0]
    assert sla_rows == 1
    assert obs_rows == 1


def test_operational_observability_handles_empty_database(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    output = run(window_days=30, save_db=False, write_csv=False, db_path=db_path)

    assert output["source_sla"].empty
    assert output["summary"]["overall_status"] == "WARNING"
    assert output["summary"]["coverage_trend_direction"] == "INSUFICIENTE"
