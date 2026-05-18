import pandas as pd

from src.paper.regime_scenario_validation import attach_regime_to_paper_results, summarize_paper_by_regime


def test_attach_and_summarize_regimes():
    results = pd.DataFrame({"start_date": ["2026-01-01"], "total_return": [0.01], "max_drawdown": [-0.02], "trades_count": [10], "win_rate": [0.6], "profit_factor": [1.2], "turnover": [10]})
    regimes = pd.DataFrame({"trade_date": ["2026-01-01"], "primary_regime": ["LATERAL"], "trend_regime": ["LATERAL"], "volatility_regime": ["NORMAL"], "liquidity_regime": ["NORMAL"]})
    attached = attach_regime_to_paper_results(results, regimes)
    summary = summarize_paper_by_regime(attached)
    assert attached["primary_regime"].iloc[0] == "LATERAL"
    assert not summary.empty
