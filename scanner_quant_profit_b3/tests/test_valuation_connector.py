import pandas as pd

from src.integration.connectors.valuation_connector import load_latest_valuation_data, normalize_valuation_data


def test_valuation_connector_missing_path_returns_empty():
    df = load_latest_valuation_data("caminho/inexistente", ["PETR4"])
    assert df.empty
    assert "fair_value" in df.columns


def test_valuation_connector_no_excel_returns_missing_rows(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    df = load_latest_valuation_data(tmp_path, ["PETR4"])
    assert len(df) == 1
    assert bool(df.loc[0, "valuation_available"]) is False
    assert df.loc[0, "valuation_governance_status"] == "VALUATION_MISSING"


def test_normalize_valuation_data_schema():
    df = normalize_valuation_data(pd.DataFrame({"ticker": ["PETR4"], "valuation_available": [True]}))
    assert bool(df.loc[0, "valuation_available"]) is True
    assert "fundamental_quality_score" in df.columns
