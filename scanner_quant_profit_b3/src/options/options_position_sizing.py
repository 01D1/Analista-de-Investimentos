"""
Options Position Sizing Integration — M010 S05.

Integrates src/risk/position_sizing.py with options paper trading.
Provides position sizing for options with options-specific rules.

Rules:
  - max_risk_per_operation  = min(max_loss, capital * risk_pct, 500 BRL default)
  - max_risk_per_underlying = 2x per operation
  - max_risk_per_expiry    = 3x per operation
  - max_exposure_strategy  = 5x per operation
  - max_size_by_liquidity  = size_by_liquidity(avg_financial_volume)
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.dashboard.data import _db_path
from src.risk.position_sizing import calculate_final_position_size, size_by_liquidity


# ── Default limits ──────────────────────────────────────────────────────────────

DEFAULT_CAPITAL = 10_000.0           # BRL — paper mode reference only
DEFAULT_RISK_PCT = 0.05              # 5 % of capital per operation
DEFAULT_MAX_RISK_OPERATION = 500.0  # BRL — hard cap for paper mode
DEFAULT_PARTICIPATION_RATE = 0.01    # 1 % participation in financial volume

# Multipliers for aggregate limits
MULT_PER_UNDERLYING = 2
MULT_PER_EXPIRY = 3
MULT_EXPOSURE_STRATEGY = 5


# ── Schema ────────────────────────────────────────────────────────────────────────

AUDIT_TABLE = "options_position_size_audit"

AUDIT_COLUMNS = [
    "audit_id          INTEGER PRIMARY KEY AUTOINCREMENT",
    "candidate_id      INTEGER",
    "proposed_size     INTEGER",
    "approved_size     INTEGER",
    "risk_amount       REAL",
    "limiting_factor   TEXT",
    "limits_json       TEXT",
    "approved_at       TEXT",
    "created_at        TEXT",
]


# ── Schema management ─────────────────────────────────────────────────────────

def ensure_position_sizing_schema() -> bool:
    """Creates or verifies options_position_size_audit table."""
    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            cur = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (AUDIT_TABLE,),
            )
            if cur.fetchone():
                return True
            cols_sql = ",\n  ".join(AUDIT_COLUMNS)
            con.execute(f"CREATE TABLE {AUDIT_TABLE} (\n  {cols_sql}\n)")
            con.commit()
            return True
    except Exception:
        return False


# ── Candidate data loading ────────────────────────────────────────────────────

def _load_candidate(candidate_id: int) -> dict[str, Any] | None:
    """Load candidate from option_structure_candidates by id."""
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM option_structure_candidates WHERE id = ?",
            (int(candidate_id),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _load_open_positions() -> list[dict[str, Any]]:
    """Load all open positions from options_positions (status in OPEN states)."""
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT * FROM options_positions
            WHERE status NOT IN ('CLOSE', 'EXPIRED', 'CANCELLED')
            ORDER BY entry_date DESC
            """,
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Options-specific sizing ────────────────────────────────────────────────────

def _compute_options_limits(
    candidate: dict[str, Any],
    capital: float,
    risk_pct: float,
    participation_rate: float,
) -> dict[str, Any]:
    """
    Compute options-specific position sizing limits.

    Returns dict with:
      max_loss, max_loss_abs, max_risk_per_operation, max_risk_per_underlying,
      max_risk_per_expiry, max_exposure_strategy, max_size_by_liquidity,
      avg_financial_volume, limiting_factor, limits_applied
    """
    # Base values from candidate
    max_loss_raw = candidate.get("max_loss")
    if max_loss_raw is None:
        max_loss_abs = 0.0
    else:
        max_loss_abs = abs(float(max_loss_raw))

    # max_loss > 0 means the candidate defines a cost (debit)
    # max_loss < 0 means net credit (no risk, limited upside)
    if max_loss_raw is not None and float(max_loss_raw) >= 0:
        # Has a defined loss risk
        max_loss_display = max_loss_abs
    else:
        # Net credit structure — risk is premium paid
        max_loss_display = max_loss_abs

    # 1. Risk per operation: min(candidate_max_loss, capital*risk_pct, hard_cap)
    candidate_risk = max_loss_display
    capital_risk = float(capital) * float(risk_pct)
    hard_cap = DEFAULT_MAX_RISK_OPERATION

    if candidate_risk <= 0:
        # No loss defined — use hard cap or capital risk
        risk_per_op = min(capital_risk, hard_cap)
        risk_per_op_source = "CAPITAL_RISK"
    else:
        risk_per_op = min(candidate_risk, capital_risk, hard_cap)
        # Identify which factor is limiting
        if risk_per_op >= candidate_risk:
            risk_per_op_source = "CANDIDATE_MAX_LOSS"
        elif risk_per_op >= capital_risk:
            risk_per_op_source = "CAPITAL_RISK"
        else:
            risk_per_op_source = "HARD_CAP"

    # 2. Aggregate limits
    max_risk_per_underlying = float(risk_per_op) * MULT_PER_UNDERLYING
    max_risk_per_expiry = float(risk_per_op) * MULT_PER_EXPIRY
    max_exposure_strategy = float(risk_per_op) * MULT_EXPOSURE_STRATEGY

    # 3. Liquidity-based size
    liquidity_score = candidate.get("liquidity_score") or 0
    avg_financial_volume = liquidity_score * 1000.0  # estimate from liquidity_score
    max_size_by_liq = size_by_liquidity(avg_financial_volume, participation_rate)

    limits = {
        "max_loss": max_loss_display,
        "max_loss_abs": max_loss_abs,
        "max_risk_per_operation": risk_per_op,
        "max_risk_per_underlying": max_risk_per_underlying,
        "max_risk_per_expiry": max_risk_per_expiry,
        "max_exposure_strategy": max_exposure_strategy,
        "max_size_by_liquidity": max_size_by_liq,
        "avg_financial_volume": avg_financial_volume,
        "limiting_factor": risk_per_op_source,
        "limits_applied": {
            "HARD_CAP": hard_cap,
            "CAPITAL_RISK": capital_risk,
            "CANDIDATE_MAX_LOSS": candidate_risk,
        },
    }
    return limits


def _compute_size_lots(
    candidate: dict[str, Any],
    limits: dict[str, Any],
) -> tuple[int, float]:
    """
    Compute final size in lots from options-specific limits.

    Returns (size_lots, risk_amount) where size_lots is integer lots.
    Risk amount is capped at max_risk_per_operation.
    """
    max_loss = limits["max_loss"]
    risk_per_op = limits["max_risk_per_operation"]

    if max_loss <= 0:
        # No cost or net credit — size = 0
        return 0, 0.0

    net_debit = candidate.get("net_debit") or 0
    net_credit = candidate.get("net_credit") or 0

    # Premium per lot: net_debit (cost) or net_credit (credit)
    if float(net_debit) > 0:
        premium_per_lot = float(net_debit)
    elif float(net_credit) > 0:
        # Credit structure — risk is the premium paid
        premium_per_lot = float(net_credit)
    else:
        premium_per_lot = max_loss  # fallback

    if premium_per_lot <= 0:
        return 0, 0.0

    # Size: risk_per_op / premium_per_lot, then cap by liquidity
    size_raw = float(risk_per_op) / premium_per_lot
    size_lots = max(1, math.floor(size_raw))  # at least 1 lot if there is a cost

    # Cap by liquidity if available
    max_liq = limits.get("max_size_by_liquidity")
    if max_liq is not None and not math.isnan(max_liq) and max_liq > 0:
        size_lots = min(size_lots, max(1, math.floor(max_liq)))

    final_risk = size_lots * premium_per_lot
    return size_lots, final_risk


def _audit_sizing_decision(
    candidate_id: int,
    proposed_size: int,
    approved_size: int,
    risk_amount: float,
    limiting_factor: str,
    limits: dict[str, Any],
) -> None:
    """Persist sizing decision to options_position_size_audit table."""
    if not ensure_position_sizing_schema():
        return

    db = _db_path()
    approved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    created_at = approved_at
    limits_json = json.dumps(limits, default=str, sort_keys=True)

    try:
        with sqlite3.connect(str(db)) as con:
            con.execute(
                f"""
                INSERT INTO {AUDIT_TABLE} (
                    candidate_id, proposed_size, approved_size,
                    risk_amount, limiting_factor, limits_json,
                    approved_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    proposed_size,
                    approved_size,
                    risk_amount,
                    limiting_factor,
                    limits_json,
                    approved_at,
                    created_at,
                ),
            )
            con.commit()
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────────

def get_options_position_size(
    candidate_id: int,
    capital: float = DEFAULT_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PCT,
    participation_rate: float = DEFAULT_PARTICIPATION_RATE,
) -> dict[str, Any]:
    """
    Calculate options position size for a candidate.

    Args:
        candidate_id: id from option_structure_candidates
        capital: total paper capital (default 10_000 BRL)
        risk_pct: fraction of capital risked per operation (default 0.05 = 5%)
        participation_rate: fraction of avg_financial_volume (default 0.01)

    Returns:
        {
            "candidate_id": int,
            "size_lots": int,
            "risk_amount": float,
            "max_loss": float,
            "limiting_factor": str,
            "limits_applied": dict,
            "sizing_notes": list[str],
            "status": str,
        }
    """
    sizing_notes: list[str] = []

    candidate = _load_candidate(int(candidate_id))
    if candidate is None:
        return {
            "candidate_id": int(candidate_id),
            "size_lots": 0,
            "risk_amount": 0.0,
            "max_loss": 0.0,
            "limiting_factor": "CANDIDATE_NOT_FOUND",
            "limits_applied": {},
            "sizing_notes": ["Candidate not found in option_structure_candidates"],
            "status": "ERROR",
        }

    underlying = candidate.get("underlying") or "UNKNOWN"
    structure_type = candidate.get("structure_type") or "UNKNOWN"
    max_loss_raw = candidate.get("max_loss")

    # Compute options-specific limits
    limits = _compute_options_limits(candidate, capital, risk_pct, participation_rate)
    max_loss = limits["max_loss"]
    limiting_factor = limits["limiting_factor"]

    # Sizing notes
    if max_loss_raw is not None and float(max_loss_raw) < 0:
        sizing_notes.append("Net credit structure — max_loss treated as premium paid")
    if limiting_factor == "HARD_CAP":
        sizing_notes.append(
            f"Capped at hard limit {DEFAULT_MAX_RISK_OPERATION} BRL; "
            f"candidate max_loss={max_loss:.2f}, capital_risk={capital*risk_pct:.2f}"
        )
    elif limiting_factor == "CAPITAL_RISK":
        sizing_notes.append(
            f"Limited by capital risk {capital*risk_pct:.2f} BRL "
            f"({risk_pct:.0%} of {capital:.0f})"
        )
    elif limiting_factor == "CANDIDATE_MAX_LOSS":
        sizing_notes.append(
            f"Limited by candidate max_loss={max_loss:.2f} BRL"
        )

    size_lots, risk_amount = _compute_size_lots(candidate, limits)

    # Add core sizing info note
    sizing_notes.append(
        f"Size={size_lots} lots, risk={risk_amount:.2f} BRL "
        f"({structure_type} on {underlying})"
    )

    # Persist audit record
    _audit_sizing_decision(
        candidate_id=int(candidate_id),
        proposed_size=size_lots,
        approved_size=size_lots,
        risk_amount=risk_amount,
        limiting_factor=limiting_factor,
        limits=limits,
    )

    return {
        "candidate_id": int(candidate_id),
        "size_lots": size_lots,
        "risk_amount": round(risk_amount, 2),
        "max_loss": round(max_loss, 2),
        "limiting_factor": limiting_factor,
        "limits_applied": limits,
        "sizing_notes": sizing_notes,
        "status": "OK",
    }


def check_position_size_limits(
    candidate_id: int,
    proposed_size_lots: int,
) -> dict[str, Any]:
    """
    Verify a proposed size against all options-specific limits.

    Returns:
        {
            "within_limits": bool,
            "violations": list[dict],
            "suggested_size": int,
            "limiting_factor": str,
            "candidate_id": int,
            "proposed_size": int,
        }
    """
    violations: list[dict] = []
    candidate = _load_candidate(int(candidate_id))
    if candidate is None:
        return {
            "within_limits": False,
            "violations": [{"factor": "CANDIDATE_NOT_FOUND", "detail": "candidate not found"}],
            "suggested_size": 0,
            "limiting_factor": "CANDIDATE_NOT_FOUND",
            "candidate_id": int(candidate_id),
            "proposed_size": proposed_size_lots,
        }

    # Compute limits for this candidate
    limits = _compute_options_limits(
        candidate, DEFAULT_CAPITAL, DEFAULT_RISK_PCT, DEFAULT_PARTICIPATION_RATE
    )

    underlying = candidate.get("underlying") or "UNKNOWN"
    maturity_date = candidate.get("maturity_date") or ""
    net_debit = candidate.get("net_debit") or 0

    premium_per_lot = float(net_debit) if float(net_debit) > 0 else limits["max_loss"]
    if premium_per_lot <= 0:
        premium_per_lot = 1.0

    proposed_risk = proposed_size_lots * premium_per_lot

    # Check 1: per-operation risk
    max_risk_op = limits["max_risk_per_operation"]
    if proposed_risk > max_risk_op:
        violations.append({
            "factor": "MAX_RISK_PER_OPERATION",
            "limit": max_risk_op,
            "proposed": proposed_risk,
            "detail": f"Proposed risk {proposed_risk:.2f} exceeds per-operation limit {max_risk_op:.2f}",
        })

    # Check 2: per-underlying aggregate limit
    open_positions = _load_open_positions()
    underlying_pos = [p for p in open_positions if (p.get("ticker") or "") == underlying]
    underlying_existing_risk = sum(
        float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        for p in underlying_pos
    )
    total_underlying_risk = underlying_existing_risk + proposed_risk
    max_risk_underlying = limits["max_risk_per_underlying"]

    if total_underlying_risk > max_risk_underlying:
        violations.append({
            "factor": "MAX_RISK_PER_UNDERLYING",
            "limit": max_risk_underlying,
            "proposed": total_underlying_risk,
            "existing": underlying_existing_risk,
            "detail": (
                f"Total risk {total_underlying_risk:.2f} exceeds per-underlying limit "
                f"{max_risk_underlying:.2f} for {underlying}"
            ),
        })

    # Check 3: per-expiry aggregate limit
    expiry_pos = [p for p in open_positions if (p.get("expiry_date") or "") == maturity_date]
    expiry_existing_risk = sum(
        float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        for p in expiry_pos
    )
    total_expiry_risk = expiry_existing_risk + proposed_risk
    max_risk_expiry = limits["max_risk_per_expiry"]

    if total_expiry_risk > max_risk_expiry:
        violations.append({
            "factor": "MAX_RISK_PER_EXPIRY",
            "limit": max_risk_expiry,
            "proposed": total_expiry_risk,
            "existing": expiry_existing_risk,
            "detail": (
                f"Total risk {total_expiry_risk:.2f} exceeds per-expiry limit "
                f"{max_risk_expiry:.2f} for expiry {maturity_date}"
            ),
        })

    # Check 4: max exposure strategy
    all_existing_risk = sum(
        float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        for p in open_positions
    )
    total_strategy_risk = all_existing_risk + proposed_risk
    max_exposure = limits["max_exposure_strategy"]

    if total_strategy_risk > max_exposure:
        violations.append({
            "factor": "MAX_EXPOSURE_STRATEGY",
            "limit": max_exposure,
            "proposed": total_strategy_risk,
            "existing": all_existing_risk,
            "detail": (
                f"Total strategy exposure {total_strategy_risk:.2f} exceeds "
                f"limit {max_exposure:.2f}"
            ),
        })

    # Check 5: liquidity cap
    max_liq = limits.get("max_size_by_liquidity")
    if max_liq is not None and not math.isnan(max_liq) and max_liq > 0:
        if proposed_size_lots > math.floor(max_liq):
            violations.append({
                "factor": "MAX_LIQUIDITY",
                "limit": int(math.floor(max_liq)),
                "proposed": proposed_size_lots,
                "detail": f"Proposed size {proposed_size_lots} exceeds liquidity cap {int(math.floor(max_liq))}",
            })

    # Determine suggested size
    if violations:
        # Compute safe size based on most constraining violation
        safe_lots = proposed_size_lots
        for v in violations:
            factor = v["factor"]
            if factor == "MAX_RISK_PER_OPERATION":
                safe_lots = min(safe_lots, int(math.floor(max_risk_op / premium_per_lot)))
            elif factor == "MAX_RISK_PER_UNDERLYING":
                avail = max_risk_underlying - underlying_existing_risk
                safe_lots = min(safe_lots, max(0, int(math.floor(avail / premium_per_lot))))
            elif factor == "MAX_RISK_PER_EXPIRY":
                avail = max_risk_expiry - expiry_existing_risk
                safe_lots = min(safe_lots, max(0, int(math.floor(avail / premium_per_lot))))
            elif factor == "MAX_EXPOSURE_STRATEGY":
                avail = max_exposure - all_existing_risk
                safe_lots = min(safe_lots, max(0, int(math.floor(avail / premium_per_lot))))
            elif factor == "MAX_LIQUIDITY" and max_liq > 0:
                safe_lots = min(safe_lots, max(0, int(math.floor(max_liq))))

        suggested_size = max(0, safe_lots)
        limiting_factor = violations[0]["factor"]
    else:
        suggested_size = proposed_size_lots
        limiting_factor = "NONE"

    return {
        "within_limits": len(violations) == 0,
        "violations": violations,
        "suggested_size": suggested_size,
        "limiting_factor": limiting_factor,
        "candidate_id": int(candidate_id),
        "proposed_size": proposed_size_lots,
    }


def calculate_options_risk_budget(
    capital: float = DEFAULT_CAPITAL,
    risk_pct: float = DEFAULT_RISK_PCT,
) -> dict[str, Any]:
    """
    Compute remaining risk budget after open positions.

    Subtracts cost_total of each open position from total risk capacity.
    Returns per-underlying and per-expiry remaining budgets.
    """
    total_risk_capacity = float(capital) * float(risk_pct)
    open_positions = _load_open_positions()

    existing_total_risk = sum(
        float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        for p in open_positions
    )
    remaining_budget = max(0.0, total_risk_capacity - existing_total_risk)

    # Per-underlying breakdown
    by_underlying: dict[str, float] = {}
    for p in open_positions:
        ticker = p.get("ticker") or "UNKNOWN"
        cost = float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        by_underlying[ticker] = by_underlying.get(ticker, 0.0) + cost

    # Per-expiry breakdown
    by_expiry: dict[str, float] = {}
    for p in open_positions:
        expiry = p.get("expiry_date") or "UNKNOWN"
        cost = float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        by_expiry[expiry] = by_expiry.get(expiry, 0.0) + cost

    # Limits per underlying/expiry
    per_underlying_limit = DEFAULT_MAX_RISK_OPERATION * MULT_PER_UNDERLYING
    per_expiry_limit = DEFAULT_MAX_RISK_OPERATION * MULT_PER_EXPIRY

    # Remaining per underlying
    remaining_by_underlying = {
        ticker: max(0.0, per_underlying_limit - risk)
        for ticker, risk in by_underlying.items()
    }
    remaining_by_expiry = {
        expiry: max(0.0, per_expiry_limit - risk)
        for expiry, risk in by_expiry.items()
    }

    return {
        "total_risk_capacity": round(total_risk_capacity, 2),
        "existing_total_risk": round(existing_total_risk, 2),
        "remaining_budget": round(remaining_budget, 2),
        "open_positions_count": len(open_positions),
        "per_underlying": {
            "limits": per_underlying_limit,
            "existing": by_underlying,
            "remaining": remaining_by_underlying,
        },
        "per_expiry": {
            "limits": per_expiry_limit,
            "existing": by_expiry,
            "remaining": remaining_by_expiry,
        },
    }


def get_aggregate_risk() -> dict[str, Any]:
    """
    Return aggregate risk summary for all open options positions.

    Groups by underlying and by expiry.
    """
    open_positions = _load_open_positions()

    # Total aggregate
    total_cost = sum(
        float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        for p in open_positions
    )
    total_max_risk = sum(
        float(p.get("max_risk") or 0) * float(p.get("quantity") or 1)
        for p in open_positions
    )

    # By underlying
    by_underlying: dict[str, dict[str, Any]] = {}
    for p in open_positions:
        ticker = p.get("ticker") or "UNKNOWN"
        cost = float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        mx_risk = float(p.get("max_risk") or 0) * float(p.get("quantity") or 1)
        if ticker not in by_underlying:
            by_underlying[ticker] = {"positions": 0, "cost_total": 0.0, "max_risk": 0.0, "position_ids": []}
        by_underlying[ticker]["positions"] += 1
        by_underlying[ticker]["cost_total"] += cost
        by_underlying[ticker]["max_risk"] += mx_risk
        by_underlying[ticker]["position_ids"].append(p.get("position_id"))

    # By expiry
    by_expiry: dict[str, dict[str, Any]] = {}
    for p in open_positions:
        expiry = p.get("expiry_date") or "UNKNOWN"
        cost = float(p.get("cost_total") or 0) * float(p.get("quantity") or 1)
        mx_risk = float(p.get("max_risk") or 0) * float(p.get("quantity") or 1)
        if expiry not in by_expiry:
            by_expiry[expiry] = {"positions": 0, "cost_total": 0.0, "max_risk": 0.0}
        by_expiry[expiry]["positions"] += 1
        by_expiry[expiry]["cost_total"] += cost
        by_expiry[expiry]["max_risk"] += mx_risk

    # Round values
    for ticker in by_underlying:
        by_underlying[ticker]["cost_total"] = round(by_underlying[ticker]["cost_total"], 2)
        by_underlying[ticker]["max_risk"] = round(by_underlying[ticker]["max_risk"], 2)

    for expiry in by_expiry:
        by_expiry[expiry]["cost_total"] = round(by_expiry[expiry]["cost_total"], 2)
        by_expiry[expiry]["max_risk"] = round(by_expiry[expiry]["max_risk"], 2)

    return {
        "total_cost_total": round(total_cost, 2),
        "total_max_risk": round(total_max_risk, 2),
        "open_positions_count": len(open_positions),
        "by_underlying": by_underlying,
        "by_expiry": by_expiry,
    }