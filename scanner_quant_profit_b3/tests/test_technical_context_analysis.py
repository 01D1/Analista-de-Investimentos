import pandas as pd

from src.technical.technical_context_analysis import (
    attach_event_context_to_technical_results,
    attach_regime_to_technical_results,
    summarize_technical_by_event_context,
    summarize_technical_by_regime,
)


def test_attach_and_summarize_regime_and_event_context():
    results = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "setup_type": ["BREAKOUT_VOLUME"], "future_return_5d": [1.0]})
    regimes = pd.DataFrame({"trade_date": ["2026-01-02"], "primary_regime": ["ALTA_TENDENCIAL"], "trend_regime": ["ALTA_TENDENCIAL"], "volatility_regime": ["NORMAL"], "liquidity_regime": ["LIQUIDEZ_FORTE"]})
    events = pd.DataFrame({"event_date": ["2026-01-02"], "ticker": ["PETR4"], "event_type": ["RESULTADO"], "impact_score": [0.8]})
    with_regime = attach_regime_to_technical_results(results, regimes)
    with_event = attach_event_context_to_technical_results(with_regime, events)
    regime_summary = summarize_technical_by_regime(with_event)
    event_summary = summarize_technical_by_event_context(with_event)
    assert with_event.loc[0, "has_event"] == 1
    assert "ALTA_TENDENCIAL" in regime_summary["regime_value"].tolist()
    assert "RESULTADO" in event_summary["context_value"].tolist()

