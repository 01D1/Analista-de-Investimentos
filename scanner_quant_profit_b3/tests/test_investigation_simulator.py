import pandas as pd

from src.paper.investigation_simulator import apply_investigation_hypothesis_to_signals, run_investigation_simulation


def _signals():
    return pd.DataFrame(
        {
            "trade_date": ["2026-01-01", "2026-01-02"],
            "ticker": ["ITUB4", "PETR4"],
            "signal_source": ["quant", "quant"],
            "signal_type": ["OBSERVAR", "OBSERVAR"],
        }
    )


def test_apply_investigation_hypothesis_exclude_asset():
    out = apply_investigation_hypothesis_to_signals(_signals(), {"hypothesis_type": "EXCLUDE_ASSET", "target": "ITUB4"})
    assert out["ticker"].tolist() == ["PETR4"]


def test_run_investigation_simulation_with_synthetic_data():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=6).astype(str).repeat(2),
            "ticker": ["ITUB4", "PETR4"] * 6,
            "open": [10, 20, 10.2, 20.2, 10.4, 20.4, 10.6, 20.6, 10.8, 20.8, 11, 21],
            "high": [10.5, 20.5, 10.7, 20.7, 10.9, 20.9, 11.1, 21.1, 11.3, 21.3, 11.5, 21.5],
            "low": [9.8, 19.8, 10, 20, 10.2, 20.2, 10.4, 20.4, 10.6, 20.6, 10.8, 20.8],
            "close": [10, 20, 10.2, 20.2, 10.4, 20.4, 10.6, 20.6, 10.8, 20.8, 11, 21],
            "volume": [100000] * 12,
            "trades": [100] * 12,
        }
    )
    result = run_investigation_simulation(
        {"start_date": "2026-01-01", "end_date": "2026-01-06", "capital": 100000},
        {"hypothesis_id": "EXCLUDE_ASSET_ITUB4", "hypothesis_type": "EXCLUDE_ASSET", "target": "ITUB4"},
        _signals(),
        prices,
    )
    assert result["hypothesis_id"] == "EXCLUDE_ASSET_ITUB4"
    assert "fragility_score_after" in result
