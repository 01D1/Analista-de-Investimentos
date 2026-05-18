import pandas as pd

from src.paper.multi_period_validation import create_validation_periods, run_multi_period_validation, summarize_multi_period_validation
from src.paper.scenario_model import build_default_paper_scenarios


def _prices(days=100):
    dates = pd.date_range("2026-01-01", periods=days).astype(str)
    return pd.DataFrame(
        [{"trade_date": d, "ticker": "PETR4", "open": 20 + i * 0.05, "high": 21 + i * 0.05, "low": 19 + i * 0.05, "close": 20 + i * 0.05, "volume": 100_000} for i, d in enumerate(dates)]
    )


def _signals():
    dates = pd.date_range("2026-01-03", periods=12, freq="7D").astype(str)
    return pd.DataFrame({"trade_date": dates, "ticker": "PETR4", "signal_source": "quant", "signal_type": "OBSERVAR", "governance_status": "APPROVED_FOR_STUDY"})


def test_create_validation_periods():
    periods = create_validation_periods("2026-01-01", "2026-04-30", window_months=2, step_months=1)
    assert len(periods) >= 2
    assert "period_id" in periods.columns


def test_run_multi_period_validation_synthetic():
    scenarios = build_default_paper_scenarios()
    scenarios = scenarios[scenarios["scenario_id"].isin(["BASELINE_SIMPLE", "ADVANCED_BASE"])]
    periods = create_validation_periods("2026-01-01", "2026-04-30", 2, 1)
    results = run_multi_period_validation(_signals(), _prices(), None, scenarios, periods)
    summary = summarize_multi_period_validation(results)
    assert not results.empty
    assert summary["scenarios_count"] == 2
    assert "positive_periods_pct" in summary


def test_run_multi_period_validation_without_data():
    results = run_multi_period_validation(pd.DataFrame(), pd.DataFrame(), None, pd.DataFrame(), pd.DataFrame())
    assert results.empty
    assert summarize_multi_period_validation(results)["robustness"] == "PAPER_SCENARIO_INSUFFICIENT_DATA"
