import pandas as pd

from src.paper.pnl_attribution import attribute_pnl_by_risk_bucket, attribute_pnl_by_signal_source, generate_pnl_attribution_report


def test_pnl_attribution_by_signal_source():
    orders = pd.DataFrame({"signal_source": ["quant", "technical"], "metadata_trade_pnl": [100, -50]})
    result = attribute_pnl_by_signal_source(orders)
    assert set(result["bucket"]) >= {"quant", "technical"}
    assert "Principal contribuição" in generate_pnl_attribution_report(result)


def test_pnl_attribution_by_risk_bucket():
    positions = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "realized_pnl": [10], "unrealized_pnl": [5]})
    risk = pd.DataFrame({"ticker": ["PETR4"], "volatility_regime": ["VOL_NORMAL"], "risk_status": ["RISK_OK"], "limiting_factor": ["VAR"]})
    result = attribute_pnl_by_risk_bucket(positions, risk)
    assert not result.empty

