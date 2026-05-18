import pandas as pd
import yaml

from src.data_quality.ri_audit import audit_ri_sites, load_ri_urls


def test_ri_url_configured_offline(tmp_path):
    empresas = tmp_path / "empresas.yaml"
    empresas.write_text(yaml.safe_dump({"PETR4": {"nome": "Petrobras", "ri_url": "https://ri.example.com"}}), encoding="utf-8")
    df = load_ri_urls(empresas_yaml=empresas)
    result = audit_ri_sites(df, check_online=False)
    assert result.iloc[0]["status"] == "NOT_CHECKED"
    assert bool(result.iloc[0]["url_configured"]) is True


def test_ri_missing_url():
    result = audit_ri_sites(pd.DataFrame([{"ticker": "VALE3", "company_name": "Vale", "ri_url": ""}]))
    assert result.iloc[0]["status"] == "MISSING_URL"
