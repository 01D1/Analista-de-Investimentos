import pandas as pd

from src.paper.cost_reduction_simulator import run_cost_reduction_variants
from src.paper.rebalance_variants import build_rebalance_variants


def _prices():
    rows = []
    for i, date in enumerate(pd.date_range("2026-01-02", periods=8).astype(str)):
        rows.append({"trade_date": date, "ticker": "PETR4", "open": 20 + i, "high": 21 + i, "low": 19 + i, "close": 20 + i, "volume": 100000})
    return pd.DataFrame(rows)


def test_run_cost_reduction_variants_returns_ranked_results():
    signals = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "signal_source": ["quant"], "governance_status": ["APPROVED_FOR_STUDY"]})
    risk = pd.DataFrame({"ticker": ["PETR4"], "trade_date": ["2026-01-02"], "recommended_size": [10], "risk_status": ["RISK_OK"]})
    variants = build_rebalance_variants().head(1)

    out = run_cost_reduction_variants(
        {"capital": 100000, "enable_rebalancing": True, "stop_loss_pct": 0.03, "take_profit_pct": 0.06, "trailing_stop_pct": 0.04},
        signals,
        _prices(),
        risk_df=risk,
        rebalance_variants=variants,
        exit_rule_variants=pd.DataFrame(),
    )

    assert not out.empty
    assert "cost_reduction" in out.columns
    assert out.iloc[0]["variant_id"] == "DISABLE_REBALANCE"
