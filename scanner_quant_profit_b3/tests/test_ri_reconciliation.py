import yaml

from src.data_quality.ri_reconciliation import detect_missing_ri_urls, suggest_ri_url_template


def test_detect_missing_ri_urls(tmp_path):
    empresas = tmp_path / "empresas.yaml"
    empresas.write_text(yaml.safe_dump({"PETR4": {"nome": "Petrobras", "ri_url": ""}}), encoding="utf-8")
    result = detect_missing_ri_urls(empresas)
    assert bool(result.iloc[0]["has_ri_url"]) is False
    assert "PREENCHER_URL_RI" in suggest_ri_url_template("PETR4", "Petrobras")
