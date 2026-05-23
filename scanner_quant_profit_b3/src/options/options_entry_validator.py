"""
Options Entry Validator — M010 S03.

validate_options_entry(candidate_id) revalida candidato antes de entrada paper.

Checks performed:
1. Stale chain for underlying (via options_health.check_stale_chain)
2. Stale bid/ask for each leg (via options_health.check_stale_bid_ask)
3. Spread current vs historical (max_spread from legs_json)
4. Volume/trades minimum (trades >= 10 per option)
5. DTE still valid (dte >= 3 and dte <= 90)


6. IV in valid range (0.05 < IV < 2.0)
7. Max risk still within limit (<= 5000 BRL)
8. Payoff still positive (payoff_ratio >= 0.3)
9. Liquidity sufficient (liquidity_score >= 30)
10. OOS status from options_oos_validator
11. Health status general

Returns: PAPER_READY / MONITOR_ONLY / BLOCKED
With: status, candidate_id, checks (list of {check, result, reason}),
      oos_status, health_status, overall_reason, validated_at
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.dashboard.data import _db_path

from src.options.options_health import (
    check_stale_bid_ask,
    check_stale_chain,
    get_options_system_health,
)
from src.options.options_oos_validator import (
    OOS_APPROVED,
    OOS_BLOCKED,
    OOS_MONITOR,
    INSUFFICIENT,
    ILLIQUID,
    get_oos_classification,
)


# ── Validation constants ────────────────────────────────────────────────────────

MAX_SPREAD_PCT = 40.0          # max acceptable bid/ask spread in %
MIN_TRADES = 10                # minimum trades per option
MIN_DTE = 3                    # minimum days to expiry
MAX_DTE = 90                   # maximum days to expiry
MIN_IV = 0.05                  # minimum implied volatility
MAX_IV = 2.0                   # maximum implied volatility
MAX_RISK_BRL = 5000.0          # maximum risk per position in BRL
MIN_PAYOFF_RATIO = 0.3         # minimum payoff ratio
MIN_LIQUIDITY_SCORE = 30.0     # minimum liquidity score

# ── Validation status constants ────────────────────────────────────────────────

STATUS_PAPER_READY = "PAPER_READY"
STATUS_MONITOR_ONLY = "MONITOR_ONLY"
STATUS_BLOCKED = "BLOCKED"


# ── Schema ────────────────────────────────────────────────────────────────────────

ENTRY_TABLE = "options_entry_validations"

ENTRY_COLUMNS = [
    "validation_id INTEGER PRIMARY KEY AUTOINCREMENT",
    "candidate_id INTEGER",
    "validated_at TEXT",
    "status TEXT",
    "oos_status TEXT",
    "health_status TEXT",
    "overall_reason TEXT",
    "checks_json TEXT",
    "created_at TEXT",
]


# ── Schema management ─────────────────────────────────────────────────────────

def ensure_entry_validation_schema() -> bool:
    """Creates or verifies options_entry_validations table."""
    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            cur = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (ENTRY_TABLE,),
            )
            if cur.fetchone():
                return True

            cols_sql = ",\n  ".join(ENTRY_COLUMNS)
            con.execute(f"CREATE TABLE {ENTRY_TABLE} (\n  {cols_sql}\n)")
            con.commit()
            return True
    except Exception:
        return False


# ── Candidate data loading ─────────────────────────────────────────────────────

def _load_candidate(candidate_id: int) -> dict[str, Any] | None:
    """Load candidate from option_structure_candidates via backtest_results mapping."""
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT c.*
            FROM option_structure_candidates c
            INNER JOIN options_backtest_results br ON br.candidate_id = c.id
            WHERE c.id = ?
            LIMIT 1
            """,
            (int(candidate_id),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _load_candidate_from_id(candidate_id: int) -> dict[str, Any] | None:
    """Load candidate directly from option_structure_candidates by id."""
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


def _load_backtest_result(candidate_id: int) -> dict[str, Any] | None:
    """Load latest backtest result for a candidate."""
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM options_backtest_results
            WHERE candidate_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (int(candidate_id),),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _parse_legs_json(legs_json_str: str | None) -> list[dict[str, Any]]:
    """Parse legs_json field."""
    if not legs_json_str:
        return []
    try:
        parsed = json.loads(legs_json_str)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_dte_from_candidate(candidate: dict[str, Any]) -> int | None:
    """Extract DTE from candidate maturity_date."""
    mat = candidate.get("maturity_date")
    if not mat:
        return None
    try:
        expiry = datetime.strptime(str(mat), "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        delta = (expiry - today).days
        return max(0, delta)
    except ValueError:
        return None


# ── Individual check functions ──────────────────────────────────────────────────

def _check_stale_chain(candidate: dict[str, Any]) -> dict[str, Any]:
    """Check 1: stale chain for underlying."""
    underlying = candidate.get("underlying") or ""
    result = check_stale_chain(underlying)
    return {
        "check": "stale_chain",
        "result": "PASS" if not result["stale"] else "FAIL",
        "reason": result["reason"] or "Chain fresh",
        "details": {"ticker": underlying, "last_update": result.get("last_update")},
    }


def _check_bid_ask(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Check 2: stale bid/ask for each leg."""
    if not legs:
        return {
            "check": "stale_bid_ask",
            "result": "FAIL",
            "reason": "No legs found in candidate",
            "details": {},
        }

    stale_legs = []
    fresh_legs = []
    for leg in legs:
        opt_ticker = leg.get("option_ticker") or leg.get("ticker") or ""
        if not opt_ticker:
            continue
        result = check_stale_bid_ask(opt_ticker)
        if result["stale"]:
            stale_legs.append(opt_ticker)
        else:
            fresh_legs.append(opt_ticker)

    if stale_legs:
        return {
            "check": "stale_bid_ask",
            "result": "FAIL",
            "reason": f"Stale bid/ask for: {', '.join(stale_legs)}",
            "details": {"stale": stale_legs, "fresh": fresh_legs},
        }
    return {
        "check": "stale_bid_ask",
        "result": "PASS",
        "reason": "All legs have fresh bid/ask",
        "details": {"fresh": fresh_legs},
    }


def _check_spread(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Check 3: spread vs historical max (uses spread_pct from legs)."""
    if not legs:
        return {
            "check": "spread",
            "result": "FAIL",
            "reason": "No legs to check spread",
            "details": {},
        }

    wide_spreads = []
    for leg in legs:
        spread_pct = leg.get("spread_pct")
        if spread_pct is None:
            continue
        if spread_pct > MAX_SPREAD_PCT:
            wide_spreads.append(f"{leg.get('option_ticker', '?')}: {spread_pct:.2f}%")

    if wide_spreads:
        return {
            "check": "spread",
            "result": "FAIL",
            "reason": f"Wide spreads: {', '.join(wide_spreads)}",
            "details": {"max_allowed": MAX_SPREAD_PCT, "wide_spreads": wide_spreads},
        }
    return {
        "check": "spread",
        "result": "PASS",
        "reason": f"All spreads within {MAX_SPREAD_PCT}%",
        "details": {},
    }


def _check_volume_trades(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Check 4: volume/trades minimum."""
    if not legs:
        return {
            "check": "volume_trades",
            "result": "FAIL",
            "reason": "No legs to check volume",
            "details": {},
        }

    low_volume = []
    for leg in legs:
        trades = leg.get("trades")
        vol = leg.get("volume")
        ticker = leg.get("option_ticker", "?")
        # Accept if trades >= MIN_TRADES OR volume > 0
        if trades is not None and trades < MIN_TRADES:
            low_volume.append(f"{ticker}: {trades} trades")
        elif trades is None and (vol is None or vol == 0):
            low_volume.append(f"{ticker}: no trades/volume")

    if low_volume:
        return {
            "check": "volume_trades",
            "result": "FAIL",
            "reason": f"Low volume: {', '.join(low_volume)}",
            "details": {"min_trades": MIN_TRADES},
        }
    return {
        "check": "volume_trades",
        "result": "PASS",
        "reason": "All legs have sufficient volume/trades",
        "details": {},
    }


def _check_dte(candidate: dict[str, Any], dte: int | None) -> dict[str, Any]:
    """Check 5: DTE still valid."""
    if dte is None:
        return {
            "check": "dte",
            "result": "FAIL",
            "reason": "Cannot compute DTE from maturity_date",
            "details": {"maturity_date": candidate.get("maturity_date")},
        }

    if dte < MIN_DTE:
        return {
            "check": "dte",
            "result": "FAIL",
            "reason": f"DTE={dte} < {MIN_DTE} (too close to expiry)",
            "details": {"dte": dte},
        }
    if dte > MAX_DTE:
        return {
            "check": "dte",
            "result": "FAIL",
            "reason": f"DTE={dte} > {MAX_DTE} (too far out)",
            "details": {"dte": dte},
        }
    return {
        "check": "dte",
        "result": "PASS",
        "reason": f"DTE={dte} within [{MIN_DTE}, {MAX_DTE}]",
        "details": {"dte": dte},
    }


def _check_iv(legs: list[dict[str, Any]]) -> dict[str, Any]:
    """Check 6: IV in valid range."""
    if not legs:
        return {
            "check": "iv",
            "result": "FAIL",
            "reason": "No legs to check IV",
            "details": {},
        }

    invalid_iv = []
    for leg in legs:
        iv = leg.get("implied_volatility")
        ticker = leg.get("option_ticker", "?")
        if iv is None:
            continue  # skip if not available
        if iv < MIN_IV or iv > MAX_IV:
            invalid_iv.append(f"{ticker}: IV={iv:.2%}")

    if invalid_iv:
        return {
            "check": "iv",
            "result": "FAIL",
            "reason": f"IV out of range: {', '.join(invalid_iv)}",
            "details": {"range": [MIN_IV, MAX_IV]},
        }
    return {
        "check": "iv",
        "result": "PASS",
        "reason": f"All IV within [{MIN_IV:.0%}, {MAX_IV:.0%}]",
        "details": {},
    }


def _check_max_risk(candidate: dict[str, Any]) -> dict[str, Any]:
    """Check 7: max risk within limit."""
    max_loss = candidate.get("max_loss") or 0
    if max_loss <= 0:
        return {
            "check": "max_risk",
            "result": "FAIL",
            "reason": f"max_loss={max_loss} <= 0 (invalid)",
            "details": {},
        }

    if max_loss > MAX_RISK_BRL:
        return {
            "check": "max_risk",
            "result": "FAIL",
            "reason": f"max_loss={max_loss:.2f} BRL > {MAX_RISK_BRL} limit",
            "details": {"max_loss": max_loss, "limit": MAX_RISK_BRL},
        }
    return {
        "check": "max_risk",
        "result": "PASS",
        "reason": f"max_loss={max_loss:.2f} BRL within {MAX_RISK_BRL} limit",
        "details": {},
    }


def _check_payoff(candidate: dict[str, Any]) -> dict[str, Any]:
    """Check 8: payoff ratio positive."""
    payoff = candidate.get("payoff_ratio") or 0
    if payoff < MIN_PAYOFF_RATIO:
        return {
            "check": "payoff",
            "result": "FAIL",
            "reason": f"payoff_ratio={payoff:.2f} < {MIN_PAYOFF_RATIO} minimum",
            "details": {},
        }
    return {
        "check": "payoff",
        "result": "PASS",
        "reason": f"payoff_ratio={payoff:.2f} >= {MIN_PAYOFF_RATIO}",
        "details": {},
    }


def _check_liquidity(candidate: dict[str, Any]) -> dict[str, Any]:
    """Check 9: liquidity sufficient."""
    liq = candidate.get("liquidity_score") or 0
    if liq < MIN_LIQUIDITY_SCORE:
        return {
            "check": "liquidity",
            "result": "FAIL",
            "reason": f"liquidity_score={liq:.1f} < {MIN_LIQUIDITY_SCORE}",
            "details": {},
        }
    return {
        "check": "liquidity",
        "result": "PASS",
        "reason": f"liquidity_score={liq:.1f} >= {MIN_LIQUIDITY_SCORE}",
        "details": {},
    }


def _check_oos(underlying: str, structure_type: str | None) -> dict[str, Any]:
    """Check 10: OOS status from options_oos_validator."""
    classifications = get_oos_classification(underlying, structure_type)
    if not classifications:
        return {
            "check": "oos",
            "result": "BLOCKED",
            "reason": "No OOS classification found",
            "details": {"oos_status": "NONE"},
        }

    latest = classifications[0]
    oos_status = latest.get("oos_status") or ""

    if oos_status == OOS_APPROVED:
        return {
            "check": "oos",
            "result": "PASS",
            "reason": f"OOS status: {oos_status}",
            "details": {"oos_status": oos_status, "confidence": latest.get("confidence", 0)},
        }
    elif oos_status == OOS_MONITOR:
        return {
            "check": "oos",
            "result": "PASS",
            "reason": f"OOS status: {oos_status} (monitoring required)",
            "details": {"oos_status": oos_status},
        }
    elif oos_status in (OOS_BLOCKED, INSUFFICIENT, ILLIQUID):
        return {
            "check": "oos",
            "result": "BLOCKED",
            "reason": f"OOS status: {oos_status}",
            "details": {"oos_status": oos_status},
        }
    else:
        return {
            "check": "oos",
            "result": "BLOCKED",
            "reason": f"Unknown OOS status: {oos_status}",
            "details": {"oos_status": oos_status},
        }


def _check_health() -> dict[str, Any]:
    """Check 11: overall system health."""
    health = get_options_system_health()
    readiness = health.get("readiness_status", "NOT_READY")
    mode = health.get("current_mode", "PAPER")

    if readiness == "READY":
        return {
            "check": "health",
            "result": "PASS",
            "reason": f"System health: {readiness}, mode: {mode}",
            "details": {"readiness": readiness, "mode": mode},
        }
    elif readiness == "DEGRADED":
        return {
            "check": "health",
            "result": "PASS",
            "reason": f"System degraded but operational: {readiness}",
            "details": {"readiness": readiness, "mode": mode},
        }
    else:
        return {
            "check": "health",
            "result": "BLOCKED",
            "reason": f"System not ready: {readiness}",
            "details": {"readiness": readiness, "mode": mode},
        }


# ── Main validator ─────────────────────────────────────────────────────────────

def validate_options_entry(candidate_id: int) -> dict[str, Any]:
    """
    Validate an option structure candidate before paper entry.

    Returns:
        {
            "status": "PAPER_READY" | "MONITOR_ONLY" | "BLOCKED",
            "candidate_id": int,
            "oos_status": str,
            "health_status": str,
            "overall_reason": str,
            "checks": [
                {"check": str, "result": str, "reason": str, "details": dict},
                ...
            ],
            "validated_at": str (ISO),
        }
    """
    validated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Load candidate data
    candidate = _load_candidate_from_id(int(candidate_id))
    if candidate is None:
        return {
            "status": STATUS_BLOCKED,
            "candidate_id": int(candidate_id),
            "oos_status": "NONE",
            "health_status": "UNKNOWN",
            "overall_reason": f"Candidate id={candidate_id} not found in option_structure_candidates",
            "checks": [],
            "validated_at": validated_at,
        }

    underlying = candidate.get("underlying") or ""
    structure_type = candidate.get("structure_type") or ""
    legs_json_str = candidate.get("legs_json")
    legs = _parse_legs_json(legs_json_str)

    # Compute DTE
    dte = _parse_dte_from_candidate(candidate)

    # Run all checks
    checks: list[dict[str, Any]] = []

    # Check 1: stale chain
    checks.append(_check_stale_chain(candidate))

    # Check 2: stale bid/ask
    checks.append(_check_bid_ask(legs))

    # Check 3: spread
    checks.append(_check_spread(legs))

    # Check 4: volume/trades
    checks.append(_check_volume_trades(legs))

    # Check 5: DTE
    checks.append(_check_dte(candidate, dte))

    # Check 6: IV
    checks.append(_check_iv(legs))

    # Check 7: max risk
    checks.append(_check_max_risk(candidate))

    # Check 8: payoff
    checks.append(_check_payoff(candidate))

    # Check 9: liquidity
    checks.append(_check_liquidity(candidate))

    # Check 10: OOS
    oos_check = _check_oos(underlying, structure_type)
    checks.append(oos_check)
    oos_status = oos_check["details"].get("oos_status", "NONE")

    # Check 11: health
    health_check = _check_health()
    checks.append(health_check)
    health_status = health_check["details"].get("readiness", "UNKNOWN")

    # Compute pass/fail counts
    pass_count = sum(1 for c in checks if c["result"] == "PASS")
    fail_count = sum(1 for c in checks if c["result"] == "FAIL")
    blocked_count = sum(1 for c in checks if c["result"] == "BLOCKED")
    total = len(checks)

    # Determine overall status
    if blocked_count > 0:
        # Any BLOCKED → overall BLOCKED
        status = STATUS_BLOCKED
        overall_reason = (
            f"BLOCKED: {blocked_count} blocking check(s). "
            f"PASS={pass_count}, FAIL={fail_count}, BLOCKED={blocked_count}/{total}."
        )
    elif fail_count > 0:
        # FAILs present → MONITOR_ONLY
        status = STATUS_MONITOR_ONLY
        overall_reason = (
            f"MONITOR_ONLY: {fail_count} failing check(s) require monitoring. "
            f"PASS={pass_count}, FAIL={fail_count}, BLOCKED={blocked_count}/{total}."
        )
    else:
        # All PASS
        status = STATUS_PAPER_READY
        overall_reason = (
            f"PAPER_READY: all {total} checks passed. "
            f"OOS={oos_status}, health={health_status}."
        )

    result = {
        "status": status,
        "candidate_id": int(candidate_id),
        "oos_status": oos_status,
        "health_status": health_status,
        "overall_reason": overall_reason,
        "checks": checks,
        "validated_at": validated_at,
        # Summary for convenience
        "pass_count": pass_count,
        "fail_count": fail_count,
        "blocked_count": blocked_count,
        "total_checks": total,
    }

    return result


# ── Persistence ─────────────────────────────────────────────────────────────────

def persist_validation_result(result: dict[str, Any]) -> None:
    """Save validation result to options_entry_validations table."""
    if not ensure_entry_validation_schema():
        return

    db = _db_path()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    checks_json = json.dumps(result.get("checks", []), default=str)

    try:
        with sqlite3.connect(str(db)) as con:
            con.execute(
                f"""
                INSERT INTO {ENTRY_TABLE} (
                    candidate_id, validated_at, status, oos_status,
                    health_status, overall_reason, checks_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.get("candidate_id"),
                    result.get("validated_at"),
                    result.get("status"),
                    result.get("oos_status"),
                    result.get("health_status"),
                    result.get("overall_reason"),
                    checks_json,
                    created_at,
                ),
            )
            con.commit()
    except Exception:
        pass


# ── Query ─────────────────────────────────────────────────────────────────────

def get_validation_history(candidate_id: int) -> list[dict[str, Any]]:
    """
    Return historical validation records for a candidate.
    Newest first.
    """
    if not ensure_entry_validation_schema():
        return []

    db = _db_path()
    try:
        with sqlite3.connect(str(db)) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                f"""
                SELECT * FROM {ENTRY_TABLE}
                WHERE candidate_id = ?
                ORDER BY validated_at DESC
                """,
                (int(candidate_id),),
            ).fetchall()
            records = []
            for row in rows:
                rec = dict(row)
                # Parse checks_json back to list
                try:
                    rec["checks"] = json.loads(rec.get("checks_json") or "[]")
                except json.JSONDecodeError:
                    rec["checks"] = []
                records.append(rec)
            return records
    except Exception:
        return []