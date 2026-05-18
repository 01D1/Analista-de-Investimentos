import numpy as np
import pandas as pd

from src.paper.simulator import run_paper_simulation


def _prices():
    dates = pd.date_range("2026-01-01", periods=8).astype(str)
    rows = []
    for i, date in enumerate(dates):
        rows.append({"trade_date": date, "ticker": "PETR4", "open": 20 + i, "high": 21 + i, "low": 19 + i, "close": 20 + i, "volume": 100_000})
    return pd.DataFrame(rows)


def test_paper_simulation_with_synthetic_signal():
    signals = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "integrated_status": ["ASSIMETRIA_A_INVESTIGAR"], "integrated_governance_status": ["INTEGRATED_APPROVED_FOR_STUDY"]})
    risk = pd.DataFrame({"ticker": ["PETR4"], "trade_date": ["2026-01-02"], "recommended_size": [10], "recommended_position_value": [200], "parametric_var_95": [5], "expected_shortfall_95": [8], "risk_status": ["RISK_OK"]})
    result = run_paper_simulation(signals, _prices(), risk_df=risk, capital=100_000, max_positions=2)
    assert not result["orders_df"].empty
    assert result["performance_summary"]["status"] == "COMPLETED"


def test_paper_simulation_advanced_stop_exit():
    prices = _prices()
    prices.loc[3, "low"] = 18
    signals = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "integrated_status": ["ASSIMETRIA_A_INVESTIGAR"], "integrated_governance_status": ["INTEGRATED_APPROVED_FOR_STUDY"]})
    risk = pd.DataFrame({"ticker": ["PETR4"], "trade_date": ["2026-01-02"], "recommended_size": [10], "recommended_position_value": [200], "parametric_var_95": [5], "expected_shortfall_95": [8], "risk_status": ["RISK_OK"]})
    result = run_paper_simulation(signals, prices, risk_df=risk, capital=100_000, stop_loss_pct=0.03)
    assert not result["exit_events_df"].empty
    assert "STOP_LOSS_PCT" in result["exit_events_df"]["exit_rule_triggered"].tolist()


def test_paper_simulation_without_prices_is_insufficient():
    result = run_paper_simulation(pd.DataFrame(), pd.DataFrame())
    assert result["performance_summary"]["status"] == "INSUFFICIENT_DATA"
