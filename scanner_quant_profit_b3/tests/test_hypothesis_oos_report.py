import pandas as pd

from src.reports.hypothesis_oos_report import generate_hypothesis_oos_report


def test_hypothesis_oos_report_markdown():
    report = generate_hypothesis_oos_report(
        {
            "hypothesis_id": "REDUCE_VOLATILITY_EXPOSURE",
            "hypothesis_type": "REDUCE_VOLATILITY_EXPOSURE",
            "target": "portfolio",
            "windows_count": 1,
            "scenarios_count": 1,
            "positive_improvement_pct": 1,
            "mean_return_delta": 0.02,
            "mean_drawdown_delta": 0.01,
            "mean_fragility_delta": -3,
            "robustness_class": "HYPOTHESIS_PROMISING",
            "governance_status": "HYPOTHESIS_APPROVED_FOR_MORE_TESTING",
        },
        pd.DataFrame({"window_id": [1], "scenario_name": ["BASE_COST"], "return_delta": [0.02], "drawdown_delta": [0.01], "fragility_delta": [-3], "trades_count": [30]}),
    )
    assert "# Relatorio OOS da Hipotese" in report
    assert "Nao recomendacao" in report
