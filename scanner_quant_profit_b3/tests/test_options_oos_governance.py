from src.options.options_oos_governance import evaluate_options_walk_forward_governance, generate_options_oos_governance_report


def test_options_oos_governance_approved_and_blocked():
    approved = evaluate_options_walk_forward_governance(
        {
            "windows_count": 4,
            "positive_windows_pct": 75,
            "mean_test_net_return": 1.2,
            "mean_test_win_rate": 55,
            "avg_test_trades": 10,
            "overfitting_windows_count": 0,
            "avg_cost_drag": 1,
            "robustness_class": "OPTIONS_WF_PROMISSOR",
        }
    )
    blocked = evaluate_options_walk_forward_governance({"windows_count": 0, "robustness_class": "OPTIONS_WF_DADOS_INSUFICIENTES"})
    assert approved["governance_status"] == "OPTIONS_OOS_APPROVED_FOR_STUDY"
    assert blocked["governance_status"] == "OPTIONS_OOS_BLOCKED_INSUFFICIENT_DATA"
    assert "não constitui recomendação" in generate_options_oos_governance_report(approved)

