"""
Options System Health Check and Stale Data Blocking — M010 S03.

Provides get_options_system_health() with:
  - last update timestamps for chain, greeks, opportunities, positions
  - source_statuses (dict per source)
  - stale_conditions (list of active stale gates)
  - recent_errors (list)
  - current_mode (PAPER/REVIEW/BLOCKED)
  - readiness_status (READY/NOT_READY/DEGRADED)
  - oos_summary (OOS classification distribution from latest run)

OOS summary includes classification counts from the most recent
options_oos_classification run (OPTIONS_OOS_APPROVED_FOR_STUDY,
OPTIONS_OOS_MONITOR_ONLY, OPTIONS_OOS_BLOCKED, INSUFFICIENT_HISTORY,
ILLIQUID_HISTORY). Monitors G-OOS1 gate (>=30 days) pass rate.

Provides stale data checks:
  - check_stale_chain(ticker) — chain updated in last 24h
  - check_stale_underlying_price(ticker) — price updated in last 1h
  - check_stale_bid_ask(option_ticker) — bid/ask recent
  - check_stale_greeks(option_ticker) — greeks calculated in last 24h
  - check_stale_opportunities() — opportunity scanner ran recently
  - check_stale_position(position_id) — snapshot in last 24h
  - _gate_stale_blocking(ticker) — combines all checks

Use sqlite3. Connect via src.dashboard.data._db_path().

Time thresholds (use datetime.now(timezone.utc) comparison):
  - chain: 24 hours
  - price: 1 hour
  - bid/ask: 5 minutes (compare captured_at timestamp)
  - greeks: 24 hours (compare captured_at)
  - opportunities: 24 hours
  - position snapshot: 24 hours

IMPORTANT:
- Do NOT fabricate data
- Do NOT execute real orders
- Return honest assessment based on actual DB timestamps
- current_mode defaults to PAPER (not OPERATIONAL)
- readiness_status: READY only if all sources fresh, else DEGRADED or NOT_READY
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from src.dashboard.data import _db_path

# ── Thresholds (in hours) ──────────────────────────────────────────────────────

THRESHOLD_CHAIN_HOURS = 24
THRESHOLD_PRICE_HOURS = 1
THRESHOLD_BIDASK_MINUTES = 5
THRESHOLD_GREEKS_HOURS = 24
THRESHOLD_OPPORTUNITIES_HOURS = 24
THRESHOLD_POSITION_HOURS = 24

# ── Readiness constants ────────────────────────────────────────────────────────

MODE_PAPER = "PAPER"
MODE_REVIEW = "REVIEW"
MODE_BLOCKED = "BLOCKED"
MODE_OPERATIONAL = "OPERATIONAL"

STATUS_READY = "READY"
STATUS_DEGRADED = "DEGRADED"
STATUS_NOT_READY = "NOT_READY"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_parse(ts: str) -> datetime | None:
    """Parse an ISO-8601 timestamp string to datetime."""
    if not ts:
        return None
    try:
        # Handle both aware and naive ISO strings
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_stale(ts: str, threshold_hours: float) -> tuple[bool, datetime | None, str]:
    """
    Check if a timestamp is stale given threshold in hours.
    Returns (stale, last_update_dt, age_str).
    """
    dt = _utc_parse(ts)
    if dt is None:
        return True, None, "no data"
    now = _utc_now()
    # If dt is naive, assume UTC and add timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    age = now - dt
    age_seconds = age.total_seconds()
    threshold_seconds = threshold_hours * 3600
    stale = age_seconds > threshold_seconds
    # Human-readable age
    if age_seconds < 60:
        age_str = f"{int(age_seconds)}s ago"
    elif age_seconds < 3600:
        age_str = f"{int(age_seconds / 60)}m ago"
    elif age_seconds < 86400:
        age_str = f"{int(age_seconds / 3600)}h ago"
    else:
        age_str = f"{int(age_seconds / 86400)}d ago"
    return stale, dt, age_str


# ── Individual stale checks ─────────────────────────────────────────────────────

def check_stale_chain(ticker: str) -> dict[str, Any]:
    """
    Check if options chain for underlying ticker is stale.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    ticker_upper = str(ticker).upper().strip()
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT captured_at
            FROM options_chain_snapshots
            WHERE underlying = ?
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (ticker_upper,),
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None or row[0] is None:
        return {
            "stale": True,
            "reason": f"No chain snapshot found for {ticker_upper}",
            "last_update": "never",
        }

    stale, _, age_str = _is_stale(str(row[0]), THRESHOLD_CHAIN_HOURS)
    return {
        "stale": stale,
        "reason": "" if not stale else f"Chain last updated {age_str} (threshold: {THRESHOLD_CHAIN_HOURS}h)",
        "last_update": str(row[0]),
        "age": age_str,
    }


def check_stale_underlying_price(ticker: str) -> dict[str, Any]:
    """
    Check if underlying price (from cotahist_daily) is stale.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    ticker_upper = str(ticker).upper().strip()
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT trade_date
            FROM cotahist_daily
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            (ticker_upper,),
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None:
        return {
            "stale": True,
            "reason": f"No price data found for {ticker_upper}",
            "last_update": "never",
        }

    # trade_date is date-only (YYYY-MM-DD), so we check if it's today's date
    trade_date_str = str(row[0])
    try:
        trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return {
            "stale": True,
            "reason": f"Unparseable trade_date: {trade_date_str}",
            "last_update": "never",
        }

    now = _utc_now()
    age = now - trade_date
    age_hours = age.total_seconds() / 3600
    stale = age_hours > THRESHOLD_PRICE_HOURS

    return {
        "stale": stale,
        "reason": "" if not stale else f"Price last updated {age_hours:.1f}h ago (threshold: {THRESHOLD_PRICE_HOURS}h)",
        "last_update": trade_date_str,
        "age_hours": round(age_hours, 1),
    }


def check_stale_bid_ask(option_ticker: str) -> dict[str, Any]:
    """
    Check if bid/ask for a specific option ticker is stale.
    Uses captured_at from options_chain_snapshots as the source of truth.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    opt = str(option_ticker).upper().strip()
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT captured_at, bid, ask, spread_pct
            FROM options_chain_snapshots
            WHERE option_ticker = ?
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (opt,),
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None or row[0] is None:
        return {
            "stale": True,
            "reason": f"No chain snapshot found for option {opt}",
            "last_update": "never",
        }

    # Use 5-minute threshold for bid/ask freshness
    stale, _, age_str = _is_stale(str(row[0]), THRESHOLD_BIDASK_MINUTES / 60)
    return {
        "stale": stale,
        "reason": (
            "" if not stale
            else f"Bid/ask last updated {age_str} (threshold: {THRESHOLD_BIDASK_MINUTES}min)"
        ),
        "last_update": str(row[0]),
        "bid": float(row[1]) if row[1] is not None else None,
        "ask": float(row[2]) if row[2] is not None else None,
        "spread_pct": float(row[3]) if row[3] is not None else None,
        "age": age_str,
    }


def check_stale_greeks(option_ticker: str) -> dict[str, Any]:
    """
    Check if Greeks for a specific option ticker are stale.
    Uses captured_at from options_greeks_snapshot.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    opt = str(option_ticker).upper().strip()
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT captured_at
            FROM options_greeks_snapshot
            WHERE ticker = ?
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (opt,),
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None or row[0] is None:
        return {
            "stale": True,
            "reason": f"No greeks snapshot found for option {opt}",
            "last_update": "never",
        }

    stale, _, age_str = _is_stale(str(row[0]), THRESHOLD_GREEKS_HOURS)
    return {
        "stale": stale,
        "reason": "" if not stale else f"Greeks last updated {age_str} (threshold: {THRESHOLD_GREEKS_HOURS}h)",
        "last_update": str(row[0]),
        "age": age_str,
    }


def check_stale_opportunities() -> dict[str, Any]:
    """
    Check if opportunity scanner ran recently.
    Uses created_at from option_structure_candidates as proxy.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT created_at
            FROM option_structure_candidates
            ORDER BY created_at DESC
            LIMIT 1
            """,
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None or row[0] is None:
        return {
            "stale": True,
            "reason": "No opportunity candidates found",
            "last_update": "never",
        }

    stale, _, age_str = _is_stale(str(row[0]), THRESHOLD_OPPORTUNITIES_HOURS)
    return {
        "stale": stale,
        "reason": (
            "" if not stale
            else f"Opportunity scanner last ran {age_str} (threshold: {THRESHOLD_OPPORTUNITIES_HOURS}h)"
        ),
        "last_update": str(row[0]),
        "age": age_str,
    }


def check_stale_position(position_id: int) -> dict[str, Any]:
    """
    Check if position snapshot is fresh.
    Returns {"stale": bool, "reason": str, "last_update": str}
    """
    db = _db_path()
    pid = int(position_id)
    try:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            """
            SELECT captured_at
            FROM options_position_snapshots
            WHERE position_id = ?
            ORDER BY captured_at DESC
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
        conn.close()
    except Exception as exc:
        return {
            "stale": True,
            "reason": f"DB error: {exc}",
            "last_update": "never",
        }

    if row is None or row[0] is None:
        return {
            "stale": True,
            "reason": f"No snapshot found for position_id={pid}",
            "last_update": "never",
        }

    stale, _, age_str = _is_stale(str(row[0]), THRESHOLD_POSITION_HOURS)
    return {
        "stale": stale,
        "reason": (
            "" if not stale
            else f"Position snapshot last updated {age_str} (threshold: {THRESHOLD_POSITION_HOURS}h)"
        ),
        "last_update": str(row[0]),
        "age": age_str,
    }


# ── Combined stale blocking gate ───────────────────────────────────────────────

def _gate_stale_blocking(ticker: str) -> dict[str, Any]:
    """
    Combine all stale checks for a ticker into a single blocking decision.
    Returns {"blocked": bool, "gates": list[dict]}
    """
    gates: list[dict[str, Any]] = []

    # Check chain
    chain_check = check_stale_chain(ticker)
    gates.append({**chain_check, "gate": "chain", "ticker": ticker})

    # Check underlying price
    price_check = check_stale_underlying_price(ticker)
    gates.append({**price_check, "gate": "underlying_price", "ticker": ticker})

    # Check opportunities
    opp_check = check_stale_opportunities()
    gates.append({**opp_check, "gate": "opportunities", "ticker": ticker})

    # Gather stale gate names
    stale_gates = [g["gate"] for g in gates if g.get("stale")]
    blocked = len(stale_gates) > 0

    return {
        "blocked": blocked,
        "gates": gates,
        "stale_gates": stale_gates,
        "blocked_reason": (
            f"Stale gates: {', '.join(stale_gates)}"
            if stale_gates
            else "All gates fresh"
        ),
    }


# ── Main health check ───────────────────────────────────────────────────────────

def get_options_system_health() -> dict[str, Any]:
    """
    Return full options system health status.

    Returns dict:
        {
            "readiness_status": "READY" | "DEGRADED" | "NOT_READY",
            "current_mode": "PAPER" | "REVIEW" | "BLOCKED" | "OPERATIONAL",
            "checked_at": str (ISO),
            "source_statuses": {
                "chain": {"stale": bool, "age": str, "count": int},
                "greeks": {"stale": bool, "age": str, "count": int},
                "opportunities": {"stale": bool, "age": str, "count": int},
                "positions": {"stale": bool, "age": str, "count": int},
                "underlying_prices": {"stale": bool, "age": str, "count": int},
            },
            "stale_conditions": [str, ...],
            "recent_errors": [str, ...],
            "last_updates": {
                "chain": str,
                "greeks": str,
                "opportunities": str,
                "positions": str,
            },
        }
    """
    db = _db_path()
    checked_at = _utc_now().isoformat(timespec="seconds")
    errors: list[str] = []
    stale_conditions: list[str] = []
    source_statuses: dict[str, dict[str, Any]] = {}

    try:
        conn = sqlite3.connect(str(db))

        # ── Chain status ───────────────────────────────────────────────────────
        try:
            chain_row = conn.execute(
                """
                SELECT MAX(captured_at), COUNT(DISTINCT underlying)
                FROM options_chain_snapshots
                """,
            ).fetchone()
            chain_max = str(chain_row[0]) if chain_row and chain_row[0] else None
            chain_stale, _, chain_age = _is_stale(chain_max or "", THRESHOLD_CHAIN_HOURS)
            chain_count = chain_row[1] if chain_row else 0
            source_statuses["chain"] = {
                "stale": chain_stale,
                "age": chain_age if chain_max else "no data",
                "last_update": chain_max or "never",
                "count": chain_count,
            }
            if chain_stale and chain_max:
                stale_conditions.append(f"chain: last updated {chain_age}")
            elif not chain_max:
                stale_conditions.append("chain: no data in options_chain_snapshots")
        except Exception as e:
            errors.append(f"chain check error: {e}")
            source_statuses["chain"] = {"stale": True, "age": "error", "count": 0}

        # ── Greeks status ──────────────────────────────────────────────────────
        try:
            greeks_row = conn.execute(
                """
                SELECT MAX(captured_at), COUNT(*)
                FROM options_greeks_snapshot
                """,
            ).fetchone()
            greeks_max = str(greeks_row[0]) if greeks_row and greeks_row[0] else None
            greeks_stale, _, greeks_age = _is_stale(greeks_max or "", THRESHOLD_GREEKS_HOURS)
            greeks_count = greeks_row[1] if greeks_row else 0
            source_statuses["greeks"] = {
                "stale": greeks_stale,
                "age": greeks_age if greeks_max else "no data",
                "last_update": greeks_max or "never",
                "count": greeks_count,
            }
            if greeks_stale and greeks_max:
                stale_conditions.append(f"greeks: last updated {greeks_age}")
            elif not greeks_max:
                stale_conditions.append("greeks: no data in options_greeks_snapshot")
        except Exception as e:
            errors.append(f"greeks check error: {e}")
            source_statuses["greeks"] = {"stale": True, "age": "error", "count": 0}

        # ── Opportunities status ───────────────────────────────────────────────
        try:
            opp_row = conn.execute(
                """
                SELECT MAX(created_at), COUNT(*)
                FROM option_structure_candidates
                """,
            ).fetchone()
            opp_max = str(opp_row[0]) if opp_row and opp_row[0] else None
            opp_stale, _, opp_age = _is_stale(opp_max or "", THRESHOLD_OPPORTUNITIES_HOURS)
            opp_count = opp_row[1] if opp_row else 0
            source_statuses["opportunities"] = {
                "stale": opp_stale,
                "age": opp_age if opp_max else "no data",
                "last_update": opp_max or "never",
                "count": opp_count,
            }
            if opp_stale and opp_max:
                stale_conditions.append(f"opportunities: last updated {opp_age}")
            elif not opp_max:
                stale_conditions.append("opportunities: no candidates in option_structure_candidates")
        except Exception as e:
            errors.append(f"opportunities check error: {e}")
            source_statuses["opportunities"] = {"stale": True, "age": "error", "count": 0}

        # ── Positions status ───────────────────────────────────────────────────
        try:
            pos_row = conn.execute(
                """
                SELECT MAX(captured_at), COUNT(*)
                FROM options_position_snapshots
                """,
            ).fetchone()
            pos_max = str(pos_row[0]) if pos_row and pos_row[0] else None
            pos_stale, _, pos_age = _is_stale(pos_max or "", THRESHOLD_POSITION_HOURS)
            pos_count = pos_row[1] if pos_row else 0
            source_statuses["positions"] = {
                "stale": pos_stale,
                "age": pos_age if pos_max else "no data",
                "last_update": pos_max or "never",
                "count": pos_count,
            }
            if pos_stale and pos_max:
                stale_conditions.append(f"positions: last updated {pos_age}")
        except Exception as e:
            errors.append(f"positions check error: {e}")
            source_statuses["positions"] = {"stale": True, "age": "error", "count": 0}

        # ── Underlying prices status ──────────────────────────────────────────
        try:
            price_row = conn.execute(
                """
                SELECT MAX(trade_date), COUNT(DISTINCT ticker)
                FROM cotahist_daily
                """,
            ).fetchone()
            price_max = str(price_row[0]) if price_row and price_row[0] else None
            # Check if price_max is today's date
            if price_max:
                try:
                    price_dt = datetime.strptime(price_max, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    age_h = (_utc_now() - price_dt).total_seconds() / 3600
                    price_stale = age_h > THRESHOLD_PRICE_HOURS
                except ValueError:
                    price_stale = True
                    age_h = 999
            else:
                price_stale = True
                age_h = 999
            price_count = price_row[1] if price_row else 0
            age_str = f"{age_h:.1f}h ago" if age_h < 24 else f"{int(age_h/24)}d ago"
            source_statuses["underlying_prices"] = {
                "stale": price_stale,
                "age": age_str if price_max else "no data",
                "last_update": price_max or "never",
                "count": price_count,
            }
            if price_stale and price_max:
                stale_conditions.append(f"underlying_prices: last updated {age_str}")
            elif not price_max:
                stale_conditions.append("underlying_prices: no data in cotahist_daily")
        except Exception as e:
            errors.append(f"underlying_prices check error: {e}")
            source_statuses["underlying_prices"] = {"stale": True, "age": "error", "count": 0}

        conn.close()

    except Exception as e:
        errors.append(f"DB connection error: {e}")

    # ── Determine mode and readiness ───────────────────────────────────────────
    # Mode: defaults to PAPER (from M009 context), escalate if blocked
    n_stale = len(stale_conditions)
    n_sources = len(source_statuses)
    fresh_sources = n_sources - sum(1 for s in source_statuses.values() if s.get("stale"))

    if n_stale == 0 and n_sources > 0:
        readiness = STATUS_READY
        mode = MODE_PAPER  # Always PAPER unless explicitly operational
    elif n_stale <= n_sources * 0.5 and fresh_sources > 0:
        readiness = STATUS_DEGRADED
        mode = MODE_REVIEW
    else:
        readiness = STATUS_NOT_READY
        mode = MODE_BLOCKED

    last_updates = {
        "chain": source_statuses.get("chain", {}).get("last_update", "never"),
        "greeks": source_statuses.get("greeks", {}).get("last_update", "never"),
        "opportunities": source_statuses.get("opportunities", {}).get("last_update", "never"),
        "positions": source_statuses.get("positions", {}).get("last_update", "never"),
        "underlying_prices": source_statuses.get("underlying_prices", {}).get("last_update", "never"),
    }

    return {
        "readiness_status": readiness,
        "current_mode": mode,
        "checked_at": checked_at,
        "source_statuses": source_statuses,
        "stale_conditions": stale_conditions,
        "recent_errors": errors,
        "last_updates": last_updates,
        # Summary counts
        "total_sources": n_sources,
        "stale_source_count": n_stale,
        "fresh_source_count": fresh_sources,
        # OOS classification from latest run
        "oos_summary": _get_oos_summary(),
    }


def _get_oos_summary() -> dict[str, Any]:
    """
    Return OOS classification summary from the most recent run.
    Includes G-OOS1 pass rate and per-status counts.
    """
    db = _db_path()
    try:
        conn = sqlite3.connect(str(db))
        # Latest run
        row = conn.execute("""
            SELECT run_id FROM options_oos_classification
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()
        if not row:
            return {"status": "no_runs", "message": "No OOS classification runs found"}
        run_id = row[0]

        counts = conn.execute("""
            SELECT oos_status, COUNT(*) as cnt
            FROM options_oos_classification
            WHERE run_id = ?
            GROUP BY oos_status
        """, (run_id,)).fetchall()

        # G-OOS1 pass rate
        g1_pass = conn.execute("""
            SELECT COUNT(*) FROM options_oos_classification
            WHERE run_id = ? AND passed_rules LIKE '%G-OOS1%'
        """, (run_id,)).fetchone()[0]

        total = conn.execute("""
            SELECT COUNT(*) FROM options_oos_classification WHERE run_id = ?
        """, (run_id,)).fetchone()[0]

        status_counts: dict[str, int] = {}
        for status, cnt in counts:
            status_counts[status] = cnt

        conn.close()
        return {
            "status": "ok",
            "run_id": run_id,
            "total_structures": total,
            "status_counts": status_counts,
            "g1_pass_count": g1_pass,
            "g1_pass_rate": round(g1_pass / total, 4) if total > 0 else 0.0,
            "g1_fail_count": total - g1_pass,
            "approved_count": status_counts.get("OPTIONS_OOS_APPROVED_FOR_STUDY", 0),
            "monitor_count": status_counts.get("OPTIONS_OOS_MONITOR_ONLY", 0),
            "blocked_count": status_counts.get("OPTIONS_OOS_BLOCKED", 0),
            "insufficient_count": status_counts.get("INSUFFICIENT_HISTORY", 0),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}