import json

import pandas as pd

from src.options.options_stability import (
    detect_options_stability_issues,
    summarize_by_dte_bucket,
    summarize_by_liquidity_bucket,
    summarize_by_moneyness_bucket,
)


def test_stability_by_dte_moneyness_and_liquidity():
    df = pd.DataFrame(
        [
            {"status": "COMPLETED", "net_return": 2, "net_pnl": 20, "dte_entry": 20, "execution_quality": "BOA", "legs_json": json.dumps([{"moneyness_class": "ATM"}])},
            {"status": "COMPLETED", "net_return": -1, "net_pnl": -10, "dte_entry": 65, "execution_quality": "ACEITAVEL", "legs_json": json.dumps([{"moneyness_class": "OTM"}])},
        ]
    )
    dte = summarize_by_dte_bucket(df)
    money = summarize_by_moneyness_bucket(df)
    liq = summarize_by_liquidity_bucket(df)
    assert "16_30" in dte["dte_bucket"].tolist()
    assert "ATM" in money["moneyness_bucket"].tolist()
    assert "BOA" in liq["liquidity_bucket"].tolist()
    assert detect_options_stability_issues(dte)

