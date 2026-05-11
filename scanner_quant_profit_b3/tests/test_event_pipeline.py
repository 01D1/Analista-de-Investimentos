import sqlite3

import pandas as pd

from src.context.connectors.local_csv_connector import load_events as load_csv_events
from src.scanners.event_pipeline import run as run_event_pipeline
from src.db.init_db import init_database


def test_local_csv_connector_loads_empty_when_missing(tmp_path):
    events = load_csv_events(csv_path=tmp_path / "missing.csv")

    assert events.empty
    assert "event_date" in events.columns


def test_event_pipeline_with_csv_example_saves_events_and_coverage(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "event_date,ticker,event_type,event_source,event_title,event_summary,event_url,impact_direction,impact_score,confidence\n"
        "2026-01-05,PETR4,,manual,Lucro acima do esperado,,http://a,,,\n"
        "2026-01-05,PETR4,,manual,Lucro acima esperado,,http://b,,,\n",
        encoding="utf-8",
    )
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO historical_backtest_results (run_id, trade_date, ticker) VALUES (1, '2026-01-05', 'PETR4')")
        con.commit()

    result = run_event_pipeline(
        start="2026-01-01",
        end="2026-01-31",
        sources=["csv"],
        csv_path=str(csv_path),
        save_db=True,
        write_csv=False,
        db_path=db_path,
    )

    assert result["events_loaded"] == 2
    assert result["events_after_dedup"] == 1
    assert result["coverage"]["signals_with_coverage"] == 1
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM market_events").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM event_coverage_runs").fetchone()[0] == 1
