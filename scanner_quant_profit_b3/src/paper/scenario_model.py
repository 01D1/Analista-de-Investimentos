"""Modelos de cenarios para validacao multi-periodo do paper trading."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class PaperScenario:
    scenario_id: str
    scenario_name: str
    signal_source: str
    start_date: str | None = None
    end_date: str | None = None
    cost_bps: float = 10
    slippage_bps: float = 5
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    trailing_stop_pct: float | None = None
    daily_loss_limit_pct: float | None = None
    max_positions: int = 5
    risk_pct: float = 0.005
    use_regime_adjustment: bool = False
    enable_rebalancing: bool = False
    metadata_json: str = "{}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["metadata_json"] = data.get("metadata_json") or "{}"
        return data


def _advanced_kwargs() -> dict:
    return {
        "stop_loss_pct": 0.03,
        "take_profit_pct": 0.10,
        "trailing_stop_pct": 0.04,
        "daily_loss_limit_pct": 0.02,
        "max_positions": 5,
        "risk_pct": 0.005,
    }


def build_default_paper_scenarios() -> pd.DataFrame:
    advanced = _advanced_kwargs()
    scenarios = [
        PaperScenario("BASELINE_SIMPLE", "BASELINE_SIMPLE", "quant", metadata_json=json.dumps({"exit_mode": "simple"})),
        PaperScenario("ADVANCED_BASE", "ADVANCED_BASE", "quant", **advanced, metadata_json=json.dumps({"exit_mode": "advanced"})),
        PaperScenario("HIGH_COSTS", "HIGH_COSTS", "quant", cost_bps=20, slippage_bps=10, **advanced),
        PaperScenario("HIGH_SLIPPAGE", "HIGH_SLIPPAGE", "quant", cost_bps=10, slippage_bps=20, **advanced),
        PaperScenario("LOW_RISK", "LOW_RISK", "quant", risk_pct=0.0025, **{k: v for k, v in advanced.items() if k != "risk_pct"}),
        PaperScenario("HIGH_RISK", "HIGH_RISK", "quant", risk_pct=0.01, **{k: v for k, v in advanced.items() if k != "risk_pct"}),
        PaperScenario("TECHNICAL_SIGNALS", "TECHNICAL_SIGNALS", "technical", **advanced),
        PaperScenario("QUANT_SIGNALS", "QUANT_SIGNALS", "quant", **advanced),
        PaperScenario("INTEGRATED_SIGNALS", "INTEGRATED_SIGNALS", "integrated", **advanced),
        PaperScenario("REGIME_ADJUSTED", "REGIME_ADJUSTED", "quant", use_regime_adjustment=True, enable_rebalancing=True, **advanced),
    ]
    return pd.DataFrame([scenario.to_dict() for scenario in scenarios])
