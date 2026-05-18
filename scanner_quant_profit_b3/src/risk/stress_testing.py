"""Stress testing simples e auditavel."""
from __future__ import annotations

import json
import pandas as pd


SCENARIOS = {
    "EQUITY_SHOCK_5": -0.05,
    "EQUITY_SHOCK_10": -0.10,
    "EQUITY_SHOCK_20": -0.20,
    "VOL_SPIKE": -0.08,
    "LIQUIDITY_SHOCK": -0.06,
    "GAP_DOWN": -0.12,
    "BLACK_SWAN": -0.30,
}


def run_single_asset_stress(position_value, shocks=None):
    shocks = shocks or [-0.02, -0.05, -0.10, -0.20]
    rows = []
    for shock in shocks:
        loss = abs(float(position_value or 0) * float(shock))
        rows.append({"scenario": f"SHOCK_{int(abs(shock) * 100)}", "estimated_loss": loss, "loss_pct": abs(float(shock)), "affected_assets": 1, "notes": "Stress hipotético para estudo."})
    return pd.DataFrame(rows)


def run_portfolio_stress(positions_df: pd.DataFrame, scenario: str):
    shock = SCENARIOS.get(scenario, -0.10)
    if positions_df is None or positions_df.empty:
        return {"scenario": scenario, "estimated_loss": 0.0, "loss_pct": abs(shock), "affected_assets": 0, "notes": "Sem posições para stress."}
    value_col = "position_value" if "position_value" in positions_df.columns else "recommended_position_value"
    total = pd.to_numeric(positions_df.get(value_col, 0), errors="coerce").fillna(0).sum()
    return {"scenario": scenario, "estimated_loss": abs(float(total) * shock), "loss_pct": abs(shock), "affected_assets": int(len(positions_df)), "notes": json.dumps({"shock": shock}, ensure_ascii=False)}

