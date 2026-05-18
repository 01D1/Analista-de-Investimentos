from src.scanners.technical_analysis_scanner import build_technical_features
from src.technical.setups import detect_technical_setups
from tests.technical_fixtures import sample_price_df


def test_detect_breakout_volume_setup():
    features = build_technical_features(sample_price_df())
    setups = detect_technical_setups(features)
    assert "setup_type" in setups.columns
    assert "BREAKOUT_VOLUME" in setups["setup_type"].tolist()

