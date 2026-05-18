import pandas as pd

from src.paper.loss_limits import check_daily_loss_limit, check_max_drawdown_limit, check_weekly_loss_limit


def test_daily_loss_limit_triggered():
    curve = pd.DataFrame({"equity": [100_000, 97_000], "drawdown": [0, -0.03]})
    assert check_daily_loss_limit(curve, 0.02)["limit_triggered"]


def test_weekly_loss_limit_triggered():
    curve = pd.DataFrame({"equity": [100_000, 99_000, 98_000, 97_000, 94_000], "drawdown": [0, -0.01, -0.02, -0.03, -0.06]})
    assert check_weekly_loss_limit(curve, 0.05)["limit_triggered"]


def test_drawdown_limit_triggered():
    curve = pd.DataFrame({"equity": [100_000, 90_000], "drawdown": [0, -0.10]})
    assert check_max_drawdown_limit(curve, 0.08)["limit_triggered"]

