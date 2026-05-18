import json

from src.technical.technical_explanations import explain_technical_score, explain_technical_setup


def test_technical_explanations_are_analytical():
    setup = explain_technical_setup({"ticker": "PETR4", "setup_type": "BREAKOUT_VOLUME", "setup_score": 80, "reasons_for": json.dumps(["rompimento"])})
    score = explain_technical_score({"technical_score_final": 70, "technical_status": "TECNICO_PROMISSOR"})
    assert "padrão a investigar" in setup
    assert "não altera o ranking principal" in score

