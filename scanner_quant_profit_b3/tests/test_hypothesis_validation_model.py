import pandas as pd

from src.paper.hypothesis_validation_model import build_hypothesis_validation_scenarios


def test_build_hypothesis_validation_scenarios_includes_cost_and_regime():
    hypotheses = pd.DataFrame({"hypothesis_id": ["REDUCE_VOLATILITY_EXPOSURE"], "hypothesis_type": ["REDUCE_VOLATILITY_EXPOSURE"], "target": ["portfolio"]})
    scenarios = build_hypothesis_validation_scenarios(hypotheses, "2026-01-01", "2026-04-30")
    assert "BASE_COST" in scenarios["scenario_name"].tolist()
    assert "HIGH_SLIPPAGE" in scenarios["scenario_name"].tolist()
    assert "REGIME_LATERAL" in scenarios["scenario_name"].tolist()
    assert scenarios["hypothesis_id"].nunique() == 1
