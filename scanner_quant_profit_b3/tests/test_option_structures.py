import pandas as pd

from src.options.structures import (
    build_bull_call_spread,
    build_long_call,
    calculate_structure_payoff,
    classify_structure_risk,
)


def test_long_call_payoff_and_risk():
    row = pd.Series({"option_ticker": "PETRA100", "option_type": "CALL", "underlying": "PETR4", "maturity_date": "2026-06-01", "strike": 30, "last_price": 1, "liquidity_score": 80, "risk_score": 70})
    structure = build_long_call(row)
    payoff = calculate_structure_payoff(structure, [29, 31, 35])

    assert structure["max_loss"] == 100
    assert structure["breakeven"] == 31
    assert payoff.iloc[-1]["payoff"] == 400
    assert classify_structure_risk(structure) == "RISCO_DEFINIDO"


def test_bull_call_spread():
    chain = pd.DataFrame(
        [
            {"option_ticker": "PETRA100", "option_type": "CALL", "underlying": "PETR4", "maturity_date": "2026-06-01", "strike": 30, "last_price": 1.2, "liquidity_score": 80, "risk_score": 70},
            {"option_ticker": "PETRB100", "option_type": "CALL", "underlying": "PETR4", "maturity_date": "2026-06-01", "strike": 32, "last_price": 0.5, "liquidity_score": 75, "risk_score": 70},
        ]
    )

    structure = build_bull_call_spread(chain, "PETR4", "2026-06-01")

    assert structure["structure_type"] == "BULL_CALL_SPREAD"
    assert structure["max_loss"] == 70
    assert structure["max_profit"] == 130
