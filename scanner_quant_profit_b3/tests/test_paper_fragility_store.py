import pandas as pd

from src.paper.paper_fragility_store import (
    load_paper_drawdown_periods,
    load_paper_fragility_by_asset,
    load_paper_fragility_by_signal_source,
    load_paper_fragility_runs,
    save_paper_fragility_run,
)


def test_paper_fragility_store_roundtrip(tmp_path):
    db = tmp_path / "fragility.db"
    summary = {"source_run_id": 1, "status": "COMPLETED", "total_trades": 2, "total_net_pnl": 10, "fragility_score": 20, "fragility_class": "ROBUSTO", "governance_status": "PAPER_FRAGILITY_OK"}
    assets = pd.DataFrame({"ticker": ["PETR4"], "trades_count": [2], "net_pnl": [10], "win_rate": [0.5], "contribution_pct": [1], "cost_drag": [1], "drawdown_contribution": [0], "fragility_score": [20], "fragility_class": ["ROBUSTO"], "metadata_json": ["{}"]})
    sources = pd.DataFrame({"signal_source": ["quant"], "trades_count": [2], "net_pnl": [10], "win_rate": [0.5], "contribution_pct": [1], "cost_drag": [1], "fragility_score": [20], "fragility_class": ["ROBUSTO"], "metadata_json": ["{}"]})
    drawdowns = pd.DataFrame({"drawdown_start": ["2026-01-01"], "drawdown_trough": ["2026-01-02"], "drawdown_recovery": [None], "depth": [-0.1], "duration_days": [1], "recovered": [False], "metadata_json": ["{}"]})
    run_id = save_paper_fragility_run(db, summary, assets, sources, drawdowns)
    assert run_id == 1
    assert len(load_paper_fragility_runs(db)) == 1
    assert len(load_paper_fragility_by_asset(db, run_id)) == 1
    assert len(load_paper_fragility_by_signal_source(db, run_id)) == 1
    assert len(load_paper_drawdown_periods(db, run_id)) == 1
