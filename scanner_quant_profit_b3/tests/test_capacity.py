from src.quant.capacity import (
    calculate_final_position_size,
    classify_capacity,
    estimate_position_size_by_capacity,
    estimate_position_size_by_risk,
    estimate_trade_capacity,
)


def test_estimate_trade_capacity_uses_participation_rate():
    assert estimate_trade_capacity(10_000_000, participation_rate=0.01) == 100_000


def test_position_size_by_risk_calculates_quantity_and_risk():
    result = estimate_position_size_by_risk(100_000, 0.01, entry_price=10, stop_price=9)

    assert result["quantity"] == 1000
    assert result["risk_amount"] == 1000
    assert result["financial_value"] == 10000


def test_position_size_by_capacity_limits_desired_size():
    result = estimate_position_size_by_capacity(100_000, desired_size=50_000, capacity=20_000)

    assert result["final_value"] == 20_000
    assert result["limiting_factor"] == "LIQUIDEZ"


def test_calculate_final_position_size_identifies_limiting_factor():
    result = calculate_final_position_size(
        capital=100_000,
        risk_pct=0.01,
        entry_price=10,
        stop_price=9,
        volume=1_000_000,
        participation_rate=0.01,
    )

    assert result["final_size"] == 1000
    assert result["capital_allocated"] == 10000
    assert result["limiting_factor"] in {"RISCO", "LIQUIDEZ", "CAPITAL"}


def test_classify_capacity_handles_low_liquidity():
    assert classify_capacity(100_000_000, capital=1_000_000, desired_allocation=50_000) == "ALTA_CAPACIDADE"
    assert classify_capacity(100_000, capital=1_000_000, desired_allocation=50_000) == "INVIAVEL"
