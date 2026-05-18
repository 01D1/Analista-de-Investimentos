from src.paper.hypothesis_universe import build_default_hypothesis_universe


def test_default_hypothesis_universe_has_required_hypotheses():
    df = build_default_hypothesis_universe()
    assert len(df) == 15
    assert "REDUCE_VOLATILITY_EXPOSURE" in df["hypothesis_id"].tolist()
    assert "REQUIRE_QUANT_TECHNICAL_AGREEMENT" in df["hypothesis_id"].tolist()
    assert df["can_simulate"].all()

