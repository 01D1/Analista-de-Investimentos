from src.options.options_backtest_governance import evaluate_options_backtest_candidate


def test_governance_blocks_insufficient_data_and_sample():
    assert evaluate_options_backtest_candidate({"total_trades": 0})["governance_status"] == "OPTIONS_BACKTEST_BLOQUEADO_DADOS"
    status = evaluate_options_backtest_candidate({"total_trades": 5, "completed_count": 5})["governance_status"]
    assert status == "OPTIONS_BACKTEST_BLOQUEADO_AMOSTRA"


def test_governance_promissor_and_rejected():
    promissor = evaluate_options_backtest_candidate(
        {"total_trades": 40, "completed_count": 35, "skipped_count": 5, "win_rate": 60, "mean_net_return": 1.2, "profit_factor": 1.5, "avg_cost_drag": 1}
    )
    rejected = evaluate_options_backtest_candidate(
        {"total_trades": 40, "completed_count": 35, "skipped_count": 5, "win_rate": 60, "mean_net_return": -0.2, "profit_factor": 0.9, "avg_cost_drag": 1}
    )
    assert promissor["governance_status"] == "OPTIONS_BACKTEST_PROMISSOR"
    assert rejected["governance_status"] == "OPTIONS_BACKTEST_REJEITADO"

