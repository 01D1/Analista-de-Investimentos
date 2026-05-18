from src.risk.position_sizing import (
    calculate_final_position_size,
    size_by_atr,
    size_by_fixed_risk,
    size_by_liquidity,
    size_by_var,
)


def test_size_by_fixed_risk():
    assert size_by_fixed_risk(100_000, 0.005, 20, 19) == 500


def test_size_by_atr_and_var_are_positive():
    assert size_by_atr(100_000, 0.005, 20, 0.5) == 500
    assert size_by_var(100_000, 0.01, 0.20) > 0


def test_size_by_liquidity_returns_value_limit():
    assert size_by_liquidity(1_000_000, 0.01) == 10_000


def test_final_position_size_uses_lowest_valid_limit():
    result = calculate_final_position_size(
        capital=100_000,
        risk_pct=0.005,
        entry_price=20,
        stop_price=19,
        atr=0.5,
        volatility=0.20,
        avg_financial_volume=100_000,
    )
    assert result["final_size"] >= 0
    assert result["limiting_factor"] in {"FIXED_RISK", "ATR", "VAR", "LIQUIDITY", "CAPITAL"}
    assert "Sizing sugerido para estudo" in result["notes"]
