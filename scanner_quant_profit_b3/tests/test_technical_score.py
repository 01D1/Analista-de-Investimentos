from src.scanners.technical_analysis_scanner import build_technical_features
from tests.technical_fixtures import sample_price_df


def test_technical_score_creates_status():
    out = build_technical_features(sample_price_df())
    assert "technical_score_final" in out.columns
    assert out.iloc[-1]["technical_status"] in {
        "TECNICO_FORTE",
        "TECNICO_PROMISSOR",
        "TECNICO_NEUTRO",
        "TECNICO_FRACO",
        "TECNICO_RISCO_ELEVADO",
        "DADOS_INSUFICIENTES",
    }

