import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_engine import (
    build_asset_intelligence_snapshot,
    calculate_data_quality_score,
    calculate_integrated_score,
    classify_integrated_status,
)


def test_asset_intelligence_scores_and_statuses():
    row = pd.Series(
        {
            "technical_score_final": 82,
            "quant_score": 78,
            "valuation_available": True,
            "upside_pct": 20,
            "primary_regime": "ALTA_TENDENCIAL",
            "event_coverage_quality": "COBERTURA_MEDIA",
            "option_available": True,
            "option_structure_score": 70,
            "regime_governance_status": "REGIME_OK",
            "governance_blocked": False,
        }
    )
    quality = calculate_data_quality_score(row)
    row["data_quality_score"] = quality
    assert quality >= 80
    assert calculate_integrated_score(row) > 65
    assert classify_integrated_status(row) == "ALTA_CONVERGENCIA_ANALITICA"


def test_asset_intelligence_detects_data_block():
    row = pd.Series({"data_quality_score": 10, "governance_blocked": False})
    assert classify_integrated_status(row) == "BLOQUEADO_DADOS_INSUFICIENTES"


def test_asset_intelligence_blocks_high_risk_status():
    row = pd.Series({"data_quality_score": 85, "governance_blocked": False, "risk_status": "RISK_BLOCKED_VAR"})
    assert classify_integrated_status(row) == "BLOQUEADO_GOVERNANCA"
    assert calculate_integrated_score(row) <= 45


def test_build_asset_intelligence_snapshot_merges_layers(tmp_path, monkeypatch):
    db = tmp_path / "scanner.db"
    init_database(db, verbose=False)

    def fake_valuation(base_path, tickers):
        return pd.DataFrame(
            {
                "ticker": tickers,
                "valuation_available": [True],
                "fair_value": [42.0],
                "upside_pct": [18.0],
                "valuation_method": ["teste"],
                "valuation_confidence": [0.6],
                "fundamental_quality_score": [pd.NA],
                "financial_health_score": [pd.NA],
                "profitability_score": [pd.NA],
                "growth_score": [pd.NA],
                "leverage_score": [pd.NA],
                "valuation_governance_status": ["VALUATION_AVAILABLE"],
            }
        )

    monkeypatch.setattr("src.integration.asset_intelligence_engine.load_latest_valuation_data", fake_valuation)
    df = build_asset_intelligence_snapshot(["PETR4"], db_path=db, include_technical=False, include_quant=False, include_events=False, include_regimes=False, include_options=False)
    assert len(df) == 1
    assert df.loc[0, "ticker"] == "PETR4"
    assert bool(df.loc[0, "valuation_available"]) is True
    assert df.loc[0, "integrated_status"] in {"BLOQUEADO_DADOS_INSUFICIENTES", "APENAS_MONITORAR", "ASSIMETRIA_A_INVESTIGAR"}
