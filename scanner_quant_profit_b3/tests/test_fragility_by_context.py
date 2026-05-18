import pandas as pd

from src.paper.fragility_by_context import analyze_paper_by_event_context, analyze_paper_by_regime, generate_context_fragility_report


def test_context_fragility():
    results = pd.DataFrame({"trade_date": ["2026-01-01"], "net_pnl": [-10], "trades_count": [3], "win_rate": [0.3], "max_drawdown": [-0.05]})
    regimes = pd.DataFrame({"trade_date": ["2026-01-01"], "primary_regime": ["LATERAL"]})
    events = pd.DataFrame({"event_date": ["2026-01-01"], "event_type": ["RESULTADO"], "has_event": [True]})
    reg = analyze_paper_by_regime(results, regimes)
    evt = analyze_paper_by_event_context(results, events)
    assert not reg.empty
    assert not evt.empty
    assert "Regime" in generate_context_fragility_report(reg, evt)
