import pandas as pd

from src.paper.hypothesis_multi_source_validation import run_hypothesis_multi_source_validation


def _prices():
    dates = pd.date_range("2026-01-01", periods=70, freq="D").astype(str)
    return pd.DataFrame(
        {
            "trade_date": list(dates) * 2,
            "ticker": ["PETR4"] * 70 + ["VALE3"] * 70,
            "open": [10.0] * 140,
            "high": [11.0] * 140,
            "low": [9.0] * 140,
            "close": [10 + i * 0.1 for i in range(70)] + [20 + i * 0.05 for i in range(70)],
            "volume": [1000] * 140,
        }
    )


def test_multi_source_validation_returns_rows():
    signals = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-02-01", periods=20, freq="D").astype(str),
            "ticker": ["PETR4", "VALE3"] * 10,
            "signal_source": ["quant"] * 20,
            "signal_score": [70] * 20,
        }
    )
    hypotheses = pd.DataFrame(
        {
            "hypothesis_id": ["EXCLUDE_LOW_SAMPLE_SIGNALS"],
            "hypothesis_type": ["EXCLUDE_LOW_SAMPLE_SIGNALS"],
            "parameters_json": ['{"min_ticker_signals": 2}'],
            "can_simulate": [True],
        }
    )
    out = run_hypothesis_multi_source_validation(
        hypotheses,
        {"quant": signals},
        _prices(),
        start_date="2026-01-01",
        end_date="2026-03-10",
        train_months=1,
        test_months=1,
        cost_scenarios=False,
    )
    assert not out.empty
    assert out.loc[0, "hypothesis_id"] == "EXCLUDE_LOW_SAMPLE_SIGNALS"

