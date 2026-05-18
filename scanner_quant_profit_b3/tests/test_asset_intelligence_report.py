import pandas as pd

from src.reports.asset_intelligence_report import generate_asset_intelligence_report, save_asset_intelligence_report


def test_asset_intelligence_report_markdown(tmp_path):
    row = pd.Series(
        {
            "ticker": "PETR4",
            "integrated_status": "APENAS_MONITORAR",
            "integrated_score": 55,
            "integrated_confidence": "BAIXA",
            "integrated_governance_status": "INTEGRATED_OBSERVATION_ONLY",
            "explanation": "ativo em estudo",
            "reasons_for": '["camada técnica em observação"]',
            "reasons_against": '["dados insuficientes"]',
            "required_actions": '["ampliar histórico"]',
        }
    )
    md = generate_asset_intelligence_report(row)
    assert "# PETR4 - Relatório Integrado" in md
    assert "não constitui recomendação" in md
    path = save_asset_intelligence_report(row, tmp_path)
    assert path.exists()
    assert "Governança Integrada" in path.read_text(encoding="utf-8")
