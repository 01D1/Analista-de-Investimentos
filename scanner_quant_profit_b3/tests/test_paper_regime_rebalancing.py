from src.paper.regime_rebalancing import adjust_exposure_by_regime


def test_regime_adjustment_reduces_lateral_and_blocks_risk():
    lateral = adjust_exposure_by_regime(100_000, {"primary_regime": "LATERAL"})
    risk = adjust_exposure_by_regime(100_000, {"risk_regime": "RISCO_ELEVADO"})
    assert lateral["adjusted_exposure"] < 100_000
    assert risk["adjusted_exposure"] == 0

