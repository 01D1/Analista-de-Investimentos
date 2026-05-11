import pandas as pd

from src.quant.event_linker import (
    classify_signal_event_context,
    link_events_to_signals,
    summarize_event_linkage,
)


def _signals():
    return pd.DataFrame(
        [
            {"id": 1, "trade_date": "2026-01-05", "ticker": "PETR4", "signal_type": "FORÇA COM LIQUIDEZ", "net_return_5d": 1.2},
            {"id": 2, "trade_date": "2026-01-06", "ticker": "VALE3", "signal_type": "OBSERVAR", "net_return_5d": -0.4},
            {"id": 3, "trade_date": "2026-01-08", "ticker": "ITUB4", "signal_type": "FRAQUEZA COM VOLUME", "net_return_5d": -0.2},
        ]
    )


def test_link_events_to_signals_marks_same_day_and_before_signal():
    events = pd.DataFrame(
        [
            {"id": 10, "event_date": "2026-01-05", "ticker": "PETR4", "event_type": "RESULTADO", "impact_direction": "POSITIVO", "impact_score": 0.9, "event_title": "Resultado"},
            {"id": 11, "event_date": "2026-01-05", "ticker": "VALE3", "event_type": "COMMODITY", "commodity_tag": "MINERIO", "impact_direction": "NEGATIVO", "impact_score": 0.7, "event_title": "Minério cai"},
        ]
    )

    linked = link_events_to_signals(_signals(), events, window_days_before=2, window_days_after=1)

    petr = linked[linked["ticker"] == "PETR4"].iloc[0]
    vale = linked[linked["ticker"] == "VALE3"].iloc[0]
    itub = linked[linked["ticker"] == "ITUB4"].iloc[0]
    assert petr["link_type"] == "SAME_DAY"
    assert petr["event_context_type"] == "MOVIMENTO_EVENT_DRIVEN"
    assert vale["link_type"] == "COMMODITY_CONTEXT"
    assert bool(itub["has_event"]) is False
    assert itub["event_context_type"] == "TECNICO_SEM_EVENTO"


def test_link_events_to_signals_uses_related_tickers_and_macro_context():
    events = pd.DataFrame(
        [
            {"id": 12, "event_date": "2026-01-08", "ticker": "", "related_tickers": "ITUB4;BBDC4", "event_type": "SETORIAL", "impact_direction": "INCERTO", "impact_score": 0.5},
            {"id": 13, "event_date": "2026-01-05", "ticker": "", "event_type": "MACRO_BRASIL", "macro_tag": "JUROS", "impact_direction": "NEGATIVO", "impact_score": 0.6},
        ]
    )

    linked = link_events_to_signals(_signals(), events, window_days_before=0, window_days_after=0)

    itub = linked[linked["ticker"] == "ITUB4"].iloc[0]
    petr = linked[linked["ticker"] == "PETR4"].iloc[0]
    assert itub["link_type"] == "SECTOR_CONTEXT"
    assert itub["event_context_type"] == "EVENTO_SETORIAL"
    assert petr["link_type"] == "MACRO_CONTEXT"
    assert petr["event_context_type"] == "EVENTO_MACRO"


def test_summarize_event_linkage_compares_event_vs_no_event():
    linked = link_events_to_signals(
        _signals(),
        pd.DataFrame(
            [{"id": 10, "event_date": "2026-01-05", "ticker": "PETR4", "event_type": "RESULTADO", "impact_direction": "POSITIVO", "impact_score": 0.9}]
        ),
    )

    summary = summarize_event_linkage(linked)

    assert summary["total_signals"] == 3
    assert summary["signals_with_same_day_event"] == 1
    assert summary["signals_without_event"] == 2
    assert summary["mean_return_with_event"] == 1.2
    assert "RESULTADO" in summary["events_by_type"]


def test_classify_signal_event_context_detects_contra_signal():
    row = {"has_event": True, "impact_direction": "NEGATIVO", "signal_type": "FORÇA COM LIQUIDEZ", "link_type": "SAME_DAY"}

    assert classify_signal_event_context(row) == "EVENTO_CONTRA_SINAL"
