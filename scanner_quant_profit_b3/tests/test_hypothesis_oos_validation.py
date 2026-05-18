import pandas as pd

from src.paper.hypothesis_oos_validation import create_hypothesis_oos_windows, run_hypothesis_oos_validation, summarize_hypothesis_oos_validation
from src.paper.hypothesis_validation_model import build_hypothesis_validation_scenarios


def _prices():
    dates = pd.date_range("2026-01-01", periods=90).astype(str)
    rows = []
    for i, date in enumerate(dates):
        rows.append({"trade_date": date, "ticker": "PETR4", "open": 20 + i * 0.05, "high": 21 + i * 0.05, "low": 19 + i * 0.05, "close": 20 + i * 0.05, "volume": 100000, "trades": 100})
    return pd.DataFrame(rows)


def _signals():
    return pd.DataFrame({"trade_date": ["2026-03-05", "2026-03-15"], "ticker": ["PETR4", "PETR4"], "signal_source": ["quant", "quant"], "signal_type": ["OBSERVAR", "OBSERVAR"]})


def test_create_hypothesis_oos_windows():
    windows = create_hypothesis_oos_windows("2026-01-01", "2026-04-30", train_months=2, test_months=1)
    assert not windows.empty
    assert {"train_start", "test_start"}.issubset(windows.columns)


def test_run_hypothesis_oos_validation_synthetic():
    hypothesis = {"hypothesis_id": "REDUCE_VOLATILITY_EXPOSURE", "hypothesis_type": "REDUCE_VOLATILITY_EXPOSURE", "target": "portfolio"}
    scenarios = build_hypothesis_validation_scenarios(pd.DataFrame([hypothesis]), "2026-01-01", "2026-03-31").head(1)
    results = run_hypothesis_oos_validation(hypothesis, _signals(), _prices(), train_months=1, test_months=1, scenarios=scenarios)
    assert not results.empty
    summary = summarize_hypothesis_oos_validation(results)
    assert "robustness_class" in summary
