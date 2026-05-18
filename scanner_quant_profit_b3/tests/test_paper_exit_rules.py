from src.paper.exit_rules import ExitRule, evaluate_exit_rules
from src.paper.order_model import PaperPosition


def test_exit_rules_stop_loss_triggered():
    pos = PaperPosition("PETR4", 10, 100)
    rule = ExitRule("s", "STOP_LOSS_PCT", True, 4, '{"stop_loss_pct": 0.03}')
    result = evaluate_exit_rules(pos, {"low": 96, "high": 101, "close": 98}, rules=[rule])
    assert result["should_exit"]
    assert result["exit_rule_triggered"] == "STOP_LOSS_PCT"


def test_exit_rules_take_profit_triggered():
    pos = PaperPosition("PETR4", 10, 100)
    rule = ExitRule("t", "TAKE_PROFIT_PCT", True, 6, '{"take_profit_pct": 0.06}')
    result = evaluate_exit_rules(pos, {"low": 99, "high": 107, "close": 106}, rules=[rule])
    assert result["should_exit"]
    assert result["exit_rule_triggered"] == "TAKE_PROFIT_PCT"


def test_exit_rules_holding_days():
    pos = PaperPosition("PETR4", 10, 100)
    pos.holding_days = 5
    rule = ExitRule("h", "FIXED_HOLDING_DAYS", True, 8, '{"holding_days": 5}')
    result = evaluate_exit_rules(pos, {"low": 99, "high": 101, "close": 100}, rules=[rule])
    assert result["should_exit"]

