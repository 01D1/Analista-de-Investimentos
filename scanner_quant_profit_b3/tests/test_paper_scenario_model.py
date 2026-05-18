from src.paper.scenario_model import PaperScenario, build_default_paper_scenarios


def test_build_default_paper_scenarios_contains_required_names():
    scenarios = build_default_paper_scenarios()
    names = set(scenarios["scenario_name"])
    assert "BASELINE_SIMPLE" in names
    assert "ADVANCED_BASE" in names
    assert "REGIME_ADJUSTED" in names
    assert {"quant", "technical", "integrated"}.issubset(set(scenarios["signal_source"]))


def test_paper_scenario_to_dict():
    scenario = PaperScenario("S1", "Teste", "quant")
    assert scenario.to_dict()["scenario_id"] == "S1"
