import json

import pandas as pd

from src.paper.drawdown_analysis import attribute_drawdown_to_positions, generate_drawdown_report, identify_drawdown_periods


def test_drawdown_periods_and_attribution():
    equity = pd.DataFrame({"trade_date": ["2026-01-01", "2026-01-02", "2026-01-03"], "equity": [100, 90, 95]})
    periods = identify_drawdown_periods(equity)
    orders = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "metadata_json": [json.dumps({"metadata_trade_pnl": -5})]})
    positions = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "market_value": [100]})
    attr = attribute_drawdown_to_positions(periods, positions, orders)
    assert not periods.empty
    assert not attr.empty
    assert "drawdown" in generate_drawdown_report(periods, attr)
