import pandas as pd
import yaml

from src.data_quality.profit_reconciliation import check_profit_freshness, suggest_profit_actions


def test_profit_reconciliation_stale_or_missing(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.safe_dump({"profit_excel_path": str(tmp_path / "missing.xlsx"), "profit_sheet_name": "Planilha1"}), encoding="utf-8")
    result = check_profit_freshness(cfg)
    assert result["status"] in {"MISSING", "STALE"}
    assert suggest_profit_actions(result)

