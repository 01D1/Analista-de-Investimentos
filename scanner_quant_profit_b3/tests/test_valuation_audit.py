from src.data_quality.valuation_audit import audit_valuation_outputs


def test_valuation_empty_base(tmp_path):
    (tmp_path / "outputs").mkdir()
    result = audit_valuation_outputs(tmp_path)
    assert result["status"] == "EMPTY"

