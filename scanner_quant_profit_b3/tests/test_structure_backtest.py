import pandas as pd

from src.options.structure_backtest import (
    calculate_structure_pnl,
    generate_structure_entries,
    run_structure_backtest,
    simulate_structure_exit,
)


def _chain():
    rows = []
    for date, price, dte in [("2026-01-02", 1.0, 40), ("2026-01-07", 1.6, 35)]:
        rows.append(
            {
                "trade_date": date,
                "captured_at": date + "T18:00:00",
                "option_ticker": "PETRA300",
                "underlying": "PETR4",
                "option_type": "CALL",
                "strike": 30,
                "maturity_date": "2026-02-20",
                "days_to_maturity": dte,
                "last_price": price,
                "bid": price - 0.05,
                "ask": price + 0.05,
                "spread_pct": 5,
                "volume": 10000,
                "trades": 100,
                "financial_volume": 100000,
                "underlying_price": 31,
                "moneyness_class": "ATM",
                "liquidity_score": 80,
                "risk_score": 70,
            }
        )
    return pd.DataFrame(rows)


def test_generate_entry_and_exit_by_holding_days():
    entries = generate_structure_entries(_chain(), "LONG_CALL", {"min_dte": 7, "max_dte": 90})
    assert len(entries) == 2
    exit_info = simulate_structure_exit(_chain(), entries.iloc[0], {"holding_days": 5})
    assert exit_info["status"] == "COMPLETED"
    assert exit_info["exit_reason"] == "HOLDING_DAYS"


def test_calculate_pnl_with_bid_ask_and_run_backtest():
    entries = generate_structure_entries(_chain(), "LONG_CALL", {"min_dte": 7, "max_dte": 90})
    exit_info = simulate_structure_exit(_chain(), entries.iloc[0], {"holding_days": 5})
    pnl = calculate_structure_pnl(entries.iloc[0], exit_info, {"cost_bps": 10, "slippage_bps": 5})
    assert pnl["net_pnl"] > 0
    results = run_structure_backtest(_chain(), "LONG_CALL", {"min_dte": 7, "max_dte": 90}, {"holding_days": 5}, {"cost_bps": 10, "slippage_bps": 5})
    assert "COMPLETED" in results["status"].tolist()

