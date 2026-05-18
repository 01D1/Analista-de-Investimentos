import pandas as pd

from src.integration.asset_intelligence_history import build_asset_history, summarize_asset_history


def test_asset_history_and_summary_trends():
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "ticker": ["PETR4", "PETR4"],
            "created_at": ["2026-01-01", "2026-01-02"],
            "integrated_score": [45, 65],
            "integrated_status": ["APENAS_MONITORAR", "ASSIMETRIA_A_INVESTIGAR"],
            "integrated_governance_status": ["INTEGRATED_OBSERVATION_ONLY", "INTEGRATED_OBSERVATION_ONLY"],
            "data_quality_score": [40, 70],
            "upside_pct": [5, 10],
            "quant_score": [50, 75],
            "primary_regime": ["LATERAL", "ALTA_TENDENCIAL"],
            "event_context_type": ["SEM_EVENTO", "EVENTO_RECENTE"],
        }
    )
    history = build_asset_history(df, "PETR4")
    summary = summarize_asset_history(history)
    assert len(history) == 2
    assert summary["score_trend"] == "MELHORANDO"
    assert summary["data_quality_trend"] == "MELHORANDO"
    assert summary["status_changes_count"] == 1


def test_asset_history_insufficient():
    summary = summarize_asset_history(pd.DataFrame())
    assert summary["score_trend"] == "INSUFICIENTE"
