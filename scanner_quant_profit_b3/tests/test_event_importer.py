import sqlite3

import pandas as pd

from src.context.event_importer import (
    load_events_from_csv,
    load_events_from_db,
    normalize_event_types,
    save_events_to_db,
)
from src.db.init_db import init_database


def test_load_and_normalize_events_from_csv(tmp_path):
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "event_date,ticker,event_type,event_source,event_title,event_summary,event_url,impact_direction,impact_score,confidence\n"
        "2026-01-05,petr4,resultado,manual,Resultado PETR4,Lucro acima,,positivo,0.8,1.4\n",
        encoding="utf-8",
    )

    events = load_events_from_csv(csv_path)

    assert len(events) == 1
    assert events.loc[0, "ticker"] == "PETR4"
    assert events.loc[0, "event_type"] == "RESULTADO"
    assert events.loc[0, "impact_direction"] == "POSITIVO"
    assert events.loc[0, "confidence"] == 1.0


def test_normalize_event_types_handles_unknown_values_and_missing_columns():
    events = pd.DataFrame([{"event_date": "2026/01/05", "ticker": " vale3 ", "event_type": "foo"}, {"event_date": "2026-01-06", "event_type": "MACRO_BRASIL"}])

    normalized = normalize_event_types(events)

    assert normalized.loc[0, "event_type"] == "DESCONHECIDO"
    assert normalized.loc[0, "ticker"] == "VALE3"
    assert normalized.loc[0, "event_date"] == "2026-01-05"
    assert normalized.loc[0, "impact_direction"] == "INCERTO"
    assert normalized.loc[1, "ticker"] == ""


def test_save_and_load_events_to_db(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    events = pd.DataFrame(
        [
            {
                "event_date": "2026-01-05",
                "ticker": "PETR4",
                "event_type": "FATO_RELEVANTE",
                "event_source": "manual",
                "event_title": "Fato relevante",
                "impact_direction": "POSITIVO",
                "impact_score": 0.7,
                "confidence": 0.9,
            }
        ]
    )

    saved = save_events_to_db(events, db_path)
    loaded = load_events_from_db(db_path, start_date="2026-01-01", end_date="2026-01-31")

    assert saved == 1
    assert loaded.loc[0, "ticker"] == "PETR4"
    assert loaded.loc[0, "event_type"] == "FATO_RELEVANTE"
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM market_events").fetchone()[0] == 1
