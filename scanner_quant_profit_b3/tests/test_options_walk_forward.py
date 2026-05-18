import pandas as pd

from src.options.options_walk_forward import (
    create_options_walk_forward_windows,
    generate_options_walk_forward_report,
    run_options_walk_forward,
    summarize_options_walk_forward,
)


def _chain():
    rows = []
    for date, price, dte in [
        ("2026-01-02", 1.0, 40),
        ("2026-01-07", 1.5, 35),
        ("2026-02-02", 1.0, 40),
        ("2026-02-07", 1.6, 35),
    ]:
        rows.append(
            {
                "trade_date": date,
                "captured_at": date + "T18:00:00",
                "option_ticker": "PETRA300",
                "underlying": "PETR4",
                "option_type": "CALL",
                "strike": 30,
                "maturity_date": "2026-03-20",
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


def test_create_options_walk_forward_windows():
    windows = create_options_walk_forward_windows("2026-01-01", "2026-04-30", train_months=1, test_months=1)
    assert len(windows) >= 2
    assert windows.loc[0, "window_id"] == 1


def test_walk_forward_empty_and_synthetic():
    empty = run_options_walk_forward(pd.DataFrame(), "LONG_CALL", {}, {}, {})
    assert empty.empty
    results = run_options_walk_forward(_chain(), "LONG_CALL", {"min_dte": 7, "max_dte": 90}, {"holding_days": 5}, {"cost_bps": 10, "slippage_bps": 5}, train_months=1, test_months=1)
    summary = summarize_options_walk_forward(results)
    assert summary["windows_count"] >= 1
    assert "OPTIONS_WF_" in summary["robustness_class"]
    assert "Walk-forward" in generate_options_walk_forward_report(summary, results)

