import pandas as pd

from src.signals.signal_coverage_requirements import evaluate_signal_coverage_requirements


def test_signal_coverage_requirements_pass_and_fail():
    coverage = pd.DataFrame(
        [
            {"signal_source": "quant", "signals_count": 40, "tickers_count": 3, "active_days_count": 12, "regimes_count": 2, "coverage_pct": 0.6, "coverage_status": "COBERTURA_MEDIA"},
            {"signal_source": "technical", "signals_count": 4, "tickers_count": 1, "active_days_count": 2, "regimes_count": 1, "coverage_pct": 0.1, "coverage_status": "COBERTURA_FRACA"},
        ]
    )
    out = evaluate_signal_coverage_requirements(coverage)
    assert out.loc[out["signal_source"] == "quant", "requirements_status"].iloc[0] == "COVERAGE_REQUIREMENTS_PASS"
    assert out.loc[out["signal_source"] == "technical", "requirements_status"].iloc[0] == "COVERAGE_REQUIREMENTS_FAIL"

