from src.quant.execution_costs import (
    calculate_b3_costs,
    calculate_round_trip_return,
    calculate_slippage,
    classify_execution_quality,
    estimate_liquidity_penalty,
)


def test_calculate_b3_costs_uses_basis_points_and_brokerage():
    result = calculate_b3_costs(100_000, brokerage=5.0, b3_fee_bps=3.25, tax_bps=1.0)

    assert result["cost_value"] == 47.5
    assert result["cost_pct"] == 0.0475


def test_calculate_slippage_adjusts_buy_and_sell_prices():
    assert calculate_slippage(100.0, slippage_bps=10, side="buy") == 100.1
    assert calculate_slippage(100.0, slippage_bps=10, side="sell") == 99.9


def test_round_trip_return_net_is_lower_than_gross_for_long_trade():
    result = calculate_round_trip_return(100.0, 110.0, side="long", cost_bps=10, slippage_bps=5)

    assert result["gross_return"] == 10.0
    assert result["entry_price_executed"] > result["entry_price_theoretical"]
    assert result["exit_price_executed"] < result["exit_price_theoretical"]
    assert result["net_return"] < result["gross_return"]
    assert result["total_cost_pct"] == 0.2
    assert result["total_slippage_pct"] == 0.1


def test_liquidity_penalty_and_execution_quality_classification():
    penalty = estimate_liquidity_penalty(volume=1_000_000, trades=100, min_volume=5_000_000, min_trades=500)

    assert penalty["penalty_pct"] > 0
    assert penalty["passes_liquidity"] is False
    assert classify_execution_quality(100_000_000, trades=20_000, spread_pct=0.05) == "EXCELENTE"
    assert classify_execution_quality(10_000_000, trades=2_000, spread_pct=0.3) == "BOA"
    assert classify_execution_quality(5_000_000, trades=500, spread_pct=0.8) == "ACEITAVEL"
    assert classify_execution_quality(1_000_000, trades=100, spread_pct=1.5) == "RUIM"
    assert classify_execution_quality(100_000, trades=10, spread_pct=5.0) == "INVIAVEL"
