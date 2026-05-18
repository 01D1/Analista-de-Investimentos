import pandas as pd

from src.reports.asset_intelligence_change_report import generate_asset_change_report, save_asset_change_report


def test_asset_intelligence_change_report(tmp_path):
    history = pd.DataFrame(
        {
            "created_at": ["2026-01-01", "2026-01-02"],
            "integrated_score": [45, 65],
            "integrated_status": ["APENAS_MONITORAR", "ASSIMETRIA_A_INVESTIGAR"],
            "governance_status": ["INTEGRATED_OBSERVATION_ONLY", "INTEGRATED_OBSERVATION_ONLY"],
            "data_quality_score": [40, 60],
        }
    )
    diffs = pd.DataFrame(
        {
            "current_created_at": ["2026-01-02"],
            "material_change": [True],
            "material_change_type": ["SCORE_CHANGE"],
            "explanation": ["Score melhorou de forma analítica."],
        }
    )
    md = generate_asset_change_report("PETR4", history, diffs)
    assert "# PETR4 - Histórico de Inteligência Integrada" in md
    assert "não constitui recomendação" in md
    path = save_asset_change_report("PETR4", history, diffs, tmp_path)
    assert path.exists()
