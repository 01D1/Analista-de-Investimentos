"""Modelos tabulares do paper trading."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


ORDER_STATUSES = {
    "SIMULATED_FILLED",
    "SIMULATED_REJECTED",
    "BLOCKED_GOVERNANCE",
    "BLOCKED_RISK",
    "BLOCKED_LIQUIDITY",
    "DATA_INSUFFICIENT",
}


@dataclass
class PaperOrder:
    order_id: str
    trade_date: str
    ticker: str
    side: str
    quantity: float
    theoretical_price: float
    simulated_execution_price: float | None = None
    order_type: str = "MARKET"
    signal_source: str = "UNKNOWN"
    signal_id: str | int | None = None
    sizing_source: str = "ANALYTICAL"
    status: str = "SIMULATED_REJECTED"
    rejection_reason: str | None = None
    execution_cost: float = 0.0
    slippage_cost: float = 0.0
    normalized_order_reason: str | None = None
    reason_confidence: float | None = None
    cost_bucket: str | None = None
    lifecycle_id: str | None = None
    parent_signal_id: str | int | None = None
    parent_position_id: str | int | None = None
    is_simulation_end_close: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    metadata_json: str = "{}"

    def to_dict(self) -> dict:
        data = asdict(self)
        if not isinstance(data.get("metadata_json"), str):
            data["metadata_json"] = json.dumps(data["metadata_json"], ensure_ascii=False)
        return data


@dataclass
class PaperPosition:
    ticker: str
    quantity: float
    avg_price: float
    market_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    risk_status: str = "DADOS_INSUFICIENTES"
    var_95: float | None = None
    expected_shortfall_95: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PaperPortfolio:
    portfolio_id: str
    capital_initial: float
    cash: float
    equity: float
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    exposure: float = 0.0
    leverage: float = 0.0
    drawdown: float = 0.0
    var_95: float = 0.0
    expected_shortfall_95: float = 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["positions"] = {k: v.to_dict() for k, v in self.positions.items()}
        return data
