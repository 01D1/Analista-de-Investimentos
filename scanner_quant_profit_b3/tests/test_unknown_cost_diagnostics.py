import pandas as pd

from src.paper.unknown_cost_diagnostics import analyze_unknown_costs, suggest_metadata_fixes


def test_analyze_unknown_costs_detects_missing_fields():
    orders = pd.DataFrame(
        [
            {"ticker": "PETR4", "trade_date": "2026-01-02", "side": "CLOSE", "execution_cost": 10, "slippage_cost": 5, "signal_source": "", "metadata_json": "{}"},
        ]
    )

    result = analyze_unknown_costs(orders)
    fixes = suggest_metadata_fixes(result["summary"])

    assert result["summary"]["unknown_orders_count"] == 1
    assert result["summary"]["unknown_cost_total"] == 15
    assert any("signal_source" in item for item in fixes)
