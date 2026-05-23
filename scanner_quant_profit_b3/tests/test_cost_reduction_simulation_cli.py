import pandas as pd

from src.scanners import cost_reduction_simulation


def test_cost_reduction_simulation_cli_run(monkeypatch, tmp_path):
    prices = pd.DataFrame({"trade_date": ["2026-01-02", "2026-01-03"], "ticker": ["PETR4", "PETR4"], "open": [20, 21], "high": [21, 22], "low": [19, 20], "close": [20, 21], "volume": [100000, 100000]})
    signals = pd.DataFrame({"trade_date": ["2026-01-02"], "ticker": ["PETR4"], "signal_source": ["quant"], "governance_status": ["APPROVED_FOR_STUDY"]})
    monkeypatch.setattr(cost_reduction_simulation, "_run_row", lambda db, paper_run_id: {"id": 2, "start_date": "2026-01-02", "end_date": "2026-01-03", "capital_initial": 100000, "metadata_json": '{"signal_source":"quant"}'})
    monkeypatch.setattr(cost_reduction_simulation, "load_paper_rebalance_events", lambda db, run_id=None: pd.DataFrame())
    monkeypatch.setattr(cost_reduction_simulation, "load_paper_signals", lambda db, source, start, end: signals)
    monkeypatch.setattr(cost_reduction_simulation, "_load_price_history", lambda db, tickers, start, end: prices)
    monkeypatch.setattr(cost_reduction_simulation, "load_latest_risk_snapshots", lambda db, tickers: pd.DataFrame({"ticker": ["PETR4"], "trade_date": ["2026-01-02"], "recommended_size": [1]}))

    result = cost_reduction_simulation.run(2, variant_type="rebalance", db_path=tmp_path / "x.db")

    assert result["status"] == "SUCCESS"
    assert result["variants_count"] > 0
