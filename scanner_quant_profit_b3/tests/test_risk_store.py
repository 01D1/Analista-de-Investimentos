import pandas as pd

from src.risk.risk_store import load_latest_risk_snapshots, save_risk_snapshots, save_volatility_estimates


def test_risk_store_persists_and_loads_latest(tmp_path):
    db = tmp_path / "risk.db"
    risk_df = pd.DataFrame(
        [
            {
                "created_at": "2026-01-01T10:00:00",
                "trade_date": "2026-01-01",
                "ticker": "PETR4",
                "price": 20,
                "position_value": 1000,
                "ensemble_vol": 0.2,
                "volatility_regime": "VOL_NORMAL",
                "parametric_var_95": 20,
                "historical_var_95": 25,
                "expected_shortfall_95": 30,
                "recommended_size": 50,
                "recommended_position_value": 1000,
                "limiting_factor": "VAR",
                "risk_status": "RISK_OK",
                "explanation": "risco estimado",
                "metadata_json": "{}",
            }
        ]
    )
    assert save_risk_snapshots(db, risk_df) == 1
    latest = load_latest_risk_snapshots(db, ["PETR4"])
    assert len(latest) == 1
    assert latest.iloc[0]["risk_status"] == "RISK_OK"


def test_volatility_store_accepts_empty(tmp_path):
    assert save_volatility_estimates(tmp_path / "risk.db", pd.DataFrame()) == 0
