from src.options.options_metrics import (
    calculate_breakeven,
    calculate_extrinsic_value,
    calculate_intrinsic_value,
    calculate_moneyness,
    calculate_option_liquidity_score,
    calculate_option_risk_score,
    calculate_spread_metrics,
)


def test_moneyness_call_and_put():
    assert calculate_moneyness("CALL", 110, 100)[1] == "ITM"
    assert calculate_moneyness("PUT", 90, 100)[1] == "ITM"
    assert calculate_moneyness("CALL", 101, 100)[1] == "ATM"


def test_intrinsic_extrinsic_and_breakeven():
    intrinsic = calculate_intrinsic_value("CALL", 110, 100)
    assert intrinsic == 10
    assert calculate_extrinsic_value(12, intrinsic) == 2
    assert calculate_breakeven("CALL", 100, 2) == 102
    assert calculate_breakeven("PUT", 100, 2) == 98


def test_spread_liquidity_and_risk_scores():
    spread, spread_pct = calculate_spread_metrics(1.0, 1.1, 1.05)
    liquidity = calculate_option_liquidity_score(100000, 500, 1_000_000, spread_pct)
    risk = calculate_option_risk_score(30, spread_pct, theta=-0.01, liquidity_score=liquidity, moneyness_class="ATM")

    assert spread == 0.1
    assert liquidity > 80
    assert risk > 70
