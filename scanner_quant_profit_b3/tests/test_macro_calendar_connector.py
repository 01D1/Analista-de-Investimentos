import json

from src.context.connectors.macro_calendar_connector import load_events


def test_macro_calendar_connector_returns_empty_when_missing(tmp_path):
    events = load_events(path=tmp_path / "missing.json")

    assert events.empty
    assert "event_date" in events.columns


def test_macro_calendar_connector_loads_valid_calendar(tmp_path):
    path = tmp_path / "calendario_economico.json"
    path.write_text(
        json.dumps(
            [
                {
                    "data": "2026-01-05",
                    "horario": "09:00",
                    "pais": "Brasil",
                    "indicador": "Decisão Copom Selic",
                    "importancia": "alta",
                    "projecao": "13,75%",
                    "anterior": "14,25%",
                    "atual": "não disponível",
                    "fonte": "manual",
                },
                {"data": "2026-02-01", "pais": "EUA", "indicador": "Payroll", "importancia": "média"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    events = load_events(start_date="2026-01-01", end_date="2026-01-31", path=path)

    assert len(events) == 1
    assert events.loc[0, "event_source"] == "calendario_economico"
    assert events.loc[0, "event_type"] == "JUROS"
    assert events.loc[0, "impact_direction"] == "INCERTO"
    assert float(events.loc[0, "confidence"]) >= 0.7
