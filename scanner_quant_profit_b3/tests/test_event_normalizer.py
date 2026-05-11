import pandas as pd

from src.context.event_normalizer import deduplicate_events, merge_duplicate_events, normalize_event_record


def test_normalize_event_record_classifies_and_scores_missing_fields():
    row = {
        "event_date": "2026/01/05",
        "ticker": " petr4 ",
        "event_title": "Lucro acima do esperado e dividendos maiores",
        "event_source": "news",
    }

    event = normalize_event_record(row)

    assert event["ticker"] == "PETR4"
    assert event["event_date"] == "2026-01-05"
    assert event["event_type"] == "RESULTADO"
    assert event["impact_direction"] == "POSITIVO"
    assert event["confidence"] > 0


def test_deduplicate_and_merge_events_selects_canonical_by_confidence():
    events = pd.DataFrame(
        [
            {"event_date": "2026-01-05", "ticker": "PETR4", "event_type": "RESULTADO", "event_title": "Resultado PETR4 1T26", "event_source": "news_hunter", "confidence": 0.6, "event_url": "a"},
            {"event_date": "2026-01-05", "ticker": "PETR4", "event_type": "RESULTADO", "event_title": "Resultado da PETR4 1T26", "event_source": "cvm", "confidence": 0.9, "event_url": "b"},
            {"event_date": "2026-01-06", "ticker": "VALE3", "event_type": "COMMODITY", "event_title": "Minério cai", "event_source": "manual", "confidence": 0.7},
        ]
    )

    marked = deduplicate_events(events)
    merged = merge_duplicate_events(marked)

    assert marked["is_duplicate"].sum() == 1
    assert len(merged) == 2
    canonical = merged[merged["ticker"] == "PETR4"].iloc[0]
    assert canonical["event_source"] == "cvm"
    assert "duplicate_urls" in str(canonical["metadata_json"])

