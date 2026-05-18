from src.options.strategy_ranking import (
    classify_option_strategy_candidate,
    explain_option_structure_score,
    score_option_structure,
)


def test_score_option_structure_classifies_interesting():
    structure = {
        "structure_type": "BULL_CALL_SPREAD",
        "underlying": "PETR4",
        "maturity_date": "2026-06-01",
        "max_profit": 200,
        "max_loss": 100,
        "payoff_ratio": 2,
        "liquidity_score": 90,
        "risk_score": 85,
    }

    scored = score_option_structure(structure, {"days_to_maturity": 30, "spread_pct": 3})

    assert scored["structure_score"] >= 60
    assert classify_option_strategy_candidate(scored) in {"ESTRUTURA_INTERESSANTE", "ASSIMETRIA_A_INVESTIGAR"}
    assert "Não é recomendação" in explain_option_structure_score(scored)


def test_score_option_structure_penalizes_liquidity():
    scored = score_option_structure({"max_profit": 100, "max_loss": 100, "payoff_ratio": 1, "liquidity_score": 10, "risk_score": 80})

    assert scored["candidate_status"] == "LIQUIDEZ_INSUFICIENTE"
