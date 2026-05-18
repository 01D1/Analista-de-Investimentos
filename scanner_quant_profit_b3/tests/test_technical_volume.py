from tests.technical_fixtures import sample_price_df
from src.technical.volume import calculate_volume_features


def test_volume_features_detect_relative_volume():
    out = calculate_volume_features(sample_price_df())
    assert out.iloc[-1]["relative_volume_20"] > 1
    assert out.iloc[-1]["volume_state"] in {"VOLUME_FORTE", "ACUMULACAO_POSSIVEL"}

