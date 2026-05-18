import pandas as pd

from src.paper.fragility_by_sector import analyze_pnl_by_sector, attach_sector_to_paper_results


def test_sector_fragility():
    results = pd.DataFrame({"ticker": ["PETR4", "VALE3"], "net_pnl": [10, -5], "trades_count": [5, 5], "win_rate": [0.6, 0.4], "cost_drag": [1, 2]})
    sectors = pd.DataFrame({"ticker": ["PETR4"], "sector": ["Energia"]})
    attached = attach_sector_to_paper_results(results, sectors)
    out = analyze_pnl_by_sector(attached)
    assert "UNKNOWN" in out["sector"].tolist()
    assert "fragility_class" in out.columns
