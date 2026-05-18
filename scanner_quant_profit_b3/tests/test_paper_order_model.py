from src.paper.order_model import PaperOrder, PaperPortfolio, PaperPosition


def test_paper_order_model_to_dict():
    order = PaperOrder("1", "2026-01-02", "PETR4", "BUY", 10, 20.0)
    data = order.to_dict()
    assert data["ticker"] == "PETR4"
    assert data["side"] == "BUY"


def test_paper_position_and_portfolio_models():
    pos = PaperPosition("PETR4", 10, 20.0, market_price=21.0)
    portfolio = PaperPortfolio("p1", 100_000, 99_000, 100_100, positions={"PETR4": pos})
    assert portfolio.to_dict()["positions"]["PETR4"]["quantity"] == 10

