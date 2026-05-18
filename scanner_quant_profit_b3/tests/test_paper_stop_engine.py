from src.paper.stop_engine import (
    calculate_atr_stop,
    calculate_fixed_stop,
    calculate_take_profit,
    check_stop_triggered,
    check_take_profit_triggered,
    update_trailing_stop,
)


def test_stop_loss_and_take_profit_levels():
    assert calculate_fixed_stop(100, 0.03) == 97
    assert calculate_take_profit(100, 0.06) == 106
    assert calculate_atr_stop(100, 2, 2) == 96


def test_stop_and_take_profit_triggered():
    assert check_stop_triggered(low=96, high=101, stop_price=97)["triggered"]
    assert check_take_profit_triggered(low=99, high=107, target_price=106)["triggered"]


def test_trailing_stop_only_moves_up_for_long():
    first = update_trailing_stop(None, 100, 0.04)
    second = update_trailing_stop(first, 110, 0.04)
    third = update_trailing_stop(second, 105, 0.04)
    assert second > first
    assert third == second

