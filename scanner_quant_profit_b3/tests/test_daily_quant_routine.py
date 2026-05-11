from datetime import datetime
import sqlite3

from src.db.init_db import init_database
from src.scanners.daily_quant_routine import run


def test_daily_quant_routine_dry_run_with_warnings(tmp_path):
    db_path = tmp_path / "scanner.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO historical_backtest_results (run_id, trade_date, ticker) VALUES (1, '2026-01-05', 'PETR4')")
        con.commit()
    csv_path = tmp_path / "events.csv"
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path.write_text(
        f"event_date,ticker,event_type,event_source,event_title,event_summary,event_url,impact_direction,impact_score,confidence\n"
        f"{today},PETR4,FATO_RELEVANTE,manual,Fato,,,,0.5,0.8\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "events.yaml"
    config_path.write_text(
        f"""
sources:
  csv:
    enabled: true
    path: "{csv_path.as_posix()}"
health:
  max_stale_days: 45
  warning_stale_days: 15
""",
        encoding="utf-8",
    )

    result = run(
        start="2026-01-01",
        end="2026-01-31",
        sources=["csv"],
        dry_run=True,
        db_path=db_path,
        config_path=config_path,
    )

    assert result["summary"]["status"] in {"DRY_RUN", "SUCCESS_WITH_WARNINGS"}
    assert result["routine_id"] is None
    assert "health" in result


def test_daily_quant_routine_save_db_records_run_and_alerts(tmp_path):
    db_path = tmp_path / "scanner.db"
    init_database(db_path, verbose=False)
    csv_path = tmp_path / "events.csv"
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path.write_text(
        "event_date,ticker,event_type,event_source,event_title,event_summary,event_url,impact_direction,impact_score,confidence\n"
        f"{today},PETR4,FATO_RELEVANTE,manual,Fato,,,,0.5,0.8\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "events.yaml"
    config_path.write_text(f"sources:\n  csv:\n    enabled: true\n    path: \"{csv_path.as_posix()}\"\n", encoding="utf-8")

    result = run(
        start="2026-01-01",
        end="2026-01-31",
        sources=["csv"],
        save_db=True,
        db_path=db_path,
        config_path=config_path,
    )

    assert result["routine_id"] == 1
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_routine_runs").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM source_health_checks").fetchone()[0] >= 1
