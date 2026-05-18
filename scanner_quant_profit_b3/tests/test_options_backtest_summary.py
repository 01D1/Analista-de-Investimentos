import pandas as pd

from src.options.options_backtest_summary import (
    evaluate_options_out_of_sample,
    generate_options_backtest_report,
    summarize_by_structure_type,
    summarize_by_underlying,
    summarize_structure_backtest,
)


def test_summarize_structure_backtest():
    df = pd.DataFrame(
        [
            {"status": "COMPLETED", "net_return": 10, "net_pnl": 100, "return_on_risk": 10, "transaction_cost": 1, "slippage_cost": 1, "spread_cost": 2, "dte_entry": 30, "entry_date": "2026-01-01", "exit_date": "2026-01-06", "structure_type": "LONG_CALL", "underlying": "PETR4"},
            {"status": "COMPLETED", "net_return": -5, "net_pnl": -50, "return_on_risk": -5, "transaction_cost": 1, "slippage_cost": 1, "spread_cost": 2, "dte_entry": 30, "entry_date": "2026-01-02", "exit_date": "2026-01-07", "structure_type": "LONG_CALL", "underlying": "PETR4"},
        ]
    )
    summary = summarize_structure_backtest(df)
    assert summary["total_trades"] == 2
    assert summary["win_rate"] == 50
    assert summary["profit_factor"] == 2
    assert "Não constitui recomendação" in generate_options_backtest_report(summary)
    assert summarize_by_structure_type(df).loc[0, "trades"] == 2
    assert summarize_by_underlying(df).loc[0, "underlying"] == "PETR4"


def test_evaluate_options_out_of_sample():
    df = pd.DataFrame(
        [
            {"status": "COMPLETED", "net_return": 5, "net_pnl": 50, "entry_date": "2026-01-01", "exit_date": "2026-01-06"},
            {"status": "COMPLETED", "net_return": -2, "net_pnl": -20, "entry_date": "2026-02-01", "exit_date": "2026-02-06"},
        ]
    )
    result = evaluate_options_out_of_sample(df, "2026-01-15")
    assert result["train"]["completed_count"] == 1
    assert result["test"]["completed_count"] == 1
    assert result["oos_status"] in {"OOS_FRAGIL", "OOS_EM_OBSERVACAO"}
