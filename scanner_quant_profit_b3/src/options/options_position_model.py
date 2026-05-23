"""Modelos para lifecycle de posições de opções — S06 M009."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------
class PositionStatus(str, Enum):
    OPEN = "OPEN"
    MONITORING = "MONITORING"
    ALERT = "ALERT"
    ADJUST = "ADJUST"
    ROLL = "ROLL"
    CLOSE = "CLOSE"
    EXPIRED = "EXPIRED"


# ---------------------------------------------------------------------------
# Tipos de alerta
# ---------------------------------------------------------------------------
class AlertType(str, Enum):
    DTE_LOW = "DTE_LOW"
    MAX_LOSS_APPROACHING = "MAX_LOSS_APPROACHING"
    PROFIT_PARTIAL_TARGET = "PROFIT_PARTIAL_TARGET"
    THETA_ACCELERATION = "THETA_ACCELERATION"
    UNDERLYING_AT_STRIKE = "UNDERLYING_AT_STRIKE"
    INVALIDATION_TRIGGERED = "INVALIDATION_TRIGGERED"
    IV_SIGNIFICANT_CHANGE = "IV_SIGNIFICANT_CHANGE"
    SPREAD_WORSENED = "SPREAD_WORSENED"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    NEWS_ADVERSE = "NEWS_ADVERSE"
    NEWS_FAVORABLE = "NEWS_FAVORABLE"
    ROLL_SUGGESTED = "ROLL_SUGGESTED"
    EXIT_SUGGESTED = "EXIT_SUGGESTED"
    STRUCTURE_EXPIRED_NEAR = "STRUCTURE_EXPIRED_NEAR"
    ADJUST_TRIGGERED = "ADJUST_TRIGGERED"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Tipos de evento lifecycle
# ---------------------------------------------------------------------------
class LifecycleEventType(str, Enum):
    CREATED = "CREATED"
    STATUS_CHANGE = "STATUS_CHANGE"
    SNAPSHOT_TAKEN = "SNAPSHOT_TAKEN"
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    ALERT_ACKNOWLEDGED = "ALERT_ACKNOWLEDGED"
    SIGNAL_EVALUATED = "SIGNAL_EVALUATED"
    SIGNAL_ACTED = "SIGNAL_ACTED"
    CLOSE_MANUAL = "CLOSE_MANUAL"
    CLOSE_STOP_LOSS = "CLOSE_STOP_LOSS"
    CLOSE_TAKE_PROFIT = "CLOSE_TAKE_PROFIT"
    CLOSE_EXPIRED = "CLOSE_EXPIRED"
    CLOSE_ADJUSTED = "CLOSE_ADJUSTED"
    ROLL_INITIATED = "ROLL_INITIATED"
    ROLL_COMPLETED = "ROLL_COMPLETED"


# ---------------------------------------------------------------------------
# Tipos de sinal de saída
# ---------------------------------------------------------------------------
class SignalType(str, Enum):
    EXIT = "EXIT"
    ADJUST = "ADJUST"
    ROLL = "ROLL"


class SignalAction(str, Enum):
    HOLD = "HOLD"
    CLOSE_FULL = "CLOSE_FULL"
    CLOSE_HALF = "CLOSE_HALF"
    ADJUST_STRIKE = "ADJUST_STRIKE"
    ADD_LEG = "ADD_LEG"
    ROLL_FORWARD = "ROLL_FORWARD"
    ROLL_UP = "ROLL_UP"
    ROLL_DOWN = "ROLL_DOWN"


# ---------------------------------------------------------------------------
# Opção (perna)
# ---------------------------------------------------------------------------
@dataclass
class OptionLeg:
    option_ticker: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    maturity_date: str
    position_side: Literal["COMPRADA", "VENDIDA"]
    quantity: int = 1
    premium: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    delta: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    gamma: Optional[float] = None
    iv: Optional[float] = None


# ---------------------------------------------------------------------------
# Posição principal
# ---------------------------------------------------------------------------
@dataclass
class OptionsPosition:
    position_id: Optional[int] = None
    candidate_id: Optional[int] = None
    ticker: str = ""
    structure_type: str = ""
    structure_subtype: Optional[str] = None
    status: PositionStatus = PositionStatus.OPEN
    direction: Optional[str] = None
    entry_date: str = ""
    expiry_date: str = ""
    dte_initial: Optional[int] = None
    quantity: int = 1
    legs: list[OptionLeg] = field(default_factory=list)
    strikes_json: Optional[str] = None
    net_debit: Optional[float] = None
    net_credit: Optional[float] = None
    premium_net: Optional[float] = None
    cost_total: Optional[float] = None
    max_risk: Optional[float] = None
    max_return: Optional[float] = None
    breakeven: Optional[float] = None
    entry_underlying_price: Optional[float] = None
    iv_entry: Optional[float] = None
    delta_entry: Optional[float] = None
    theta_entry: Optional[float] = None
    vega_entry: Optional[float] = None
    gamma_entry: Optional[float] = None
    original_thesis: Optional[str] = None
    invalidation_condition: Optional[str] = None
    exit_condition: Optional[str] = None
    roll_condition: Optional[str] = None
    source_type: str = "PAPER"
    is_simulated: bool = True
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "candidate_id": self.candidate_id,
            "ticker": self.ticker,
            "structure_type": self.structure_type,
            "status": self.status.value if isinstance(self.status, PositionStatus) else self.status,
            "direction": self.direction,
            "entry_date": self.entry_date,
            "expiry_date": self.expiry_date,
            "dte_initial": self.dte_initial,
            "quantity": self.quantity,
            "legs": [asdict(l) for l in self.legs],
            "cost_total": self.cost_total,
            "max_risk": self.max_risk,
            "max_return": self.max_return,
            "breakeven": self.breakeven,
            "entry_underlying_price": self.entry_underlying_price,
            "iv_entry": self.iv_entry,
            "source_type": self.source_type,
            "is_simulated": self.is_simulated,
        }


# ---------------------------------------------------------------------------
# Snapshot de monitoramento
# ---------------------------------------------------------------------------
@dataclass
class PositionSnapshot:
    snapshot_id: Optional[int] = None
    position_id: int = 0
    captured_at: str = ""
    underlying_price: Optional[float] = None
    option_prices: Optional[dict[str, float]] = None
    structure_value: Optional[float] = None
    pnl_reais: Optional[float] = None
    pnl_pct: Optional[float] = None
    dte_current: Optional[int] = None
    theta_decay_accumulated: Optional[float] = None
    theta_current: Optional[float] = None
    iv_current: Optional[float] = None
    iv_change_pct: Optional[float] = None
    delta_current: Optional[float] = None
    vega_current: Optional[float] = None
    gamma_current: Optional[float] = None
    distance_to_strike_pct: Optional[float] = None
    distance_to_breakeven_pct: Optional[float] = None
    liquidity_score: Optional[float] = None
    spread_pct: Optional[float] = None
    thesis_status: Optional[str] = None
    days_to_event: Optional[int] = None
    event_context_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Alerta
# ---------------------------------------------------------------------------
@dataclass
class PositionAlert:
    alert_id: Optional[int] = None
    position_id: int = 0
    snapshot_id: Optional[int] = None
    alert_type: AlertType = AlertType.DTE_LOW
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    is_active: bool = True
    is_acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Evento de lifecycle
# ---------------------------------------------------------------------------
@dataclass
class LifecycleEvent:
    event_id: Optional[int] = None
    position_id: int = 0
    event_type: LifecycleEventType = LifecycleEventType.CREATED
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    reason: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Sinal de saída/ajuste/rolagem
# ---------------------------------------------------------------------------
@dataclass
class ExitSignal:
    signal_id: Optional[int] = None
    position_id: int = 0
    signal_type: SignalType = SignalType.EXIT
    action: SignalAction = SignalAction.HOLD
    reason: str = ""
    confidence: Optional[float] = None
    trigger_snapshot_id: Optional[int] = None
    is_acted_upon: bool = False
    acted_at: Optional[str] = None
    action_outcome: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


from dataclasses import asdict