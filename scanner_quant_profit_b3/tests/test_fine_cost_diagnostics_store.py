import pandas as pd

from src.paper.fine_cost_diagnostics_store import (
    load_exit_rule_cost_diagnostics,
    load_lifecycle_costs,
    load_order_reason_diagnostics,
    load_rebalance_cost_diagnostics,
    load_unknown_cost_diagnostics,
    save_fine_cost_diagnostics,
)


def test_save_and_load_fine_cost_diagnostics(tmp_path):
    db = tmp_path / "scanner_quant.db"
    save_fine_cost_diagnostics(
        db,
        2,
        order_reasons_df=pd.DataFrame([{"id": 1, "ticker": "PETR4", "trade_date": "2026-01-02", "signal_source": "quant", "normalized_order_reason": "ENTRY_SIGNAL", "reason_confidence": 1.0, "is_unknown": False, "missing_metadata_fields_json": "[]", "metadata_json": "{}"}]),
        lifecycle_df=pd.DataFrame([{"lifecycle_id": "PETR4-001", "ticker": "PETR4", "entry_cost": 1, "exit_cost": 2, "rebalance_cost": 0, "total_cost": 3, "metadata_json": "{}"}]),
        rebalance_df=pd.DataFrame([{"ticker": "PETR4", "rebalance_cost_total": 0, "rebalance_slippage_total": 0, "rebalance_orders_count": 0, "rebalance_cost_class": "REBALANCE_DATA_INSUFFICIENT", "metadata_json": "{}"}]),
        exit_rule_df=pd.DataFrame([{"exit_rule": "EXIT_STOP_LOSS", "exit_count": 1, "cost_drag": 2, "exit_rule_cost_class": "EXIT_RULE_COSTLY", "metadata_json": "{}"}]),
        unknown_summary={"unknown_orders_count": 1, "unknown_cost_total": 2, "unknown_slippage_total": 1, "missing_fields_summary_json": "{}", "required_metadata_fixes_json": "[]", "metadata_json": "{}"},
    )

    assert len(load_order_reason_diagnostics(db, run_id=2)) == 1
    assert len(load_lifecycle_costs(db, run_id=2)) == 1
    assert len(load_rebalance_cost_diagnostics(db, run_id=2)) == 1
    assert len(load_exit_rule_cost_diagnostics(db, run_id=2)) == 1
    assert len(load_unknown_cost_diagnostics(db, run_id=2)) == 1
