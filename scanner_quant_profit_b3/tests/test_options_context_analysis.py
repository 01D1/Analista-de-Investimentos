import pandas as pd

from src.options.options_context_analysis import (
    attach_event_context_to_options_results,
    attach_regime_context_to_options_results,
    generate_options_context_report,
    summarize_options_by_event_context,
    summarize_options_by_regime,
)


def test_attach_and_summarize_regime_event_context():
    results = pd.DataFrame([{"entry_date": "2026-01-02", "underlying": "PETR4", "status": "COMPLETED", "net_return": 2, "net_pnl": 20}])
    regimes = pd.DataFrame([{"trade_date": "2026-01-02", "primary_regime": "ALTA_TENDENCIAL", "trend_regime": "ALTA_TENDENCIAL"}])
    events = pd.DataFrame([{"event_date": "2026-01-02", "ticker": "PETR4", "event_type": "RESULTADO", "impact_score": 0.8}])
    with_regime = attach_regime_context_to_options_results(results, regimes)
    with_event = attach_event_context_to_options_results(with_regime, events)
    regime_summary = summarize_options_by_regime(with_event)
    event_summary = summarize_options_by_event_context(with_event)
    assert with_event.loc[0, "primary_regime"] == "ALTA_TENDENCIAL"
    assert bool(with_event.loc[0, "has_event"]) is True
    assert regime_summary.loc[0, "trades"] == 1
    assert "Contexto" in generate_options_context_report(regime_summary, event_summary)

