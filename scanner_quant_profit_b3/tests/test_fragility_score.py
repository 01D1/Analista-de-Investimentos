from src.paper.fragility_score import calculate_fragility_score


def test_fragility_score_classes_insufficient_and_robust():
    assert calculate_fragility_score({"trades_count": 1})["fragility_class"] == "DADOS_INSUFICIENTES"
    robust = calculate_fragility_score({"trades_count": 10, "net_pnl": 100, "cost_drag": 1, "win_rate": 0.7})
    assert robust["fragility_class"] in {"ROBUSTO", "OBSERVACAO"}
