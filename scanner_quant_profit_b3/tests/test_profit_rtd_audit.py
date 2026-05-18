from pathlib import Path

import pandas as pd
import yaml

from src.data_quality.profit_rtd_audit import audit_profit_excel


def test_profit_excel_missing(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"profit_excel_path": str(tmp_path / "missing.xlsx"), "profit_sheet_name": "Planilha1"}), encoding="utf-8")
    result = audit_profit_excel(cfg)
    assert result["status"] == "MISSING"
    assert result["file_exists"] is False


def test_profit_excel_valid(tmp_path):
    excel = tmp_path / "profit.xlsx"
    pd.DataFrame({"ticker": ["PETR4"], "last": [10.5], "open": [10], "high": [11], "low": [9], "volume": [1000], "trades": [20]}).to_excel(excel, sheet_name="Planilha1", index=False)
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"profit_excel_path": str(excel), "profit_sheet_name": "Planilha1"}), encoding="utf-8")
    result = audit_profit_excel(cfg)
    assert result["file_exists"] is True
    assert result["assets_count"] == 1
    assert result["critical_fields_ok"] is True

