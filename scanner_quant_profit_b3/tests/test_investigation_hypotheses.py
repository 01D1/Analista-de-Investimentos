import pandas as pd

from src.paper.investigation_hypotheses import generate_hypotheses_from_fragility


def test_generate_hypotheses_from_fragility_excludes_critical_asset():
    assets = pd.DataFrame(
        {
            "ticker": ["ITUB4"],
            "net_pnl": [-1939.95],
            "cost_drag": [1152.18],
            "drawdown_contribution": [0.02],
            "fragility_score": [76],
            "fragility_class": ["CRITICO"],
        }
    )
    sources = pd.DataFrame({"signal_source": ["quant"], "trades_count": [46], "net_pnl": [5539], "cost_drag": [783], "fragility_score": [34], "fragility_class": ["OBSERVACAO"]})
    hypotheses = generate_hypotheses_from_fragility(assets, sources)
    assert "EXCLUDE_ASSET_ITUB4" in hypotheses["hypothesis_id"].tolist()
    assert "LIMIT_ASSET_COST_ITUB4" in hypotheses["hypothesis_id"].tolist()


def test_generate_hypotheses_from_fragility_detects_rebalance_cost():
    assets = pd.DataFrame()
    sources = pd.DataFrame({"signal_source": ["rebalance"], "trades_count": [53], "net_pnl": [0], "cost_drag": [1819], "fragility_score": [30], "fragility_class": ["OBSERVACAO"]})
    hypotheses = generate_hypotheses_from_fragility(assets, sources)
    assert "DISABLE_REBALANCING" in hypotheses["hypothesis_id"].tolist()
