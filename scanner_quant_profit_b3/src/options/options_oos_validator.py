"""
Options OOS Validator — Governança Out-of-Sample para estruturas de opções.

Responsabilidade:
  - Classificar estruturas via regras G-OOS (1-8) com诚实的数据限制报告
  - Separar dados em train/val/test windows mesmo com dados mínimos
  - Persistir classificações em options_oos_classification
  - Não fabricate dados, não relaxar regras, não aprovar artificialmente

G-OOS Rules:
  G-OOS1: available_days >= 30 → INSUFFICIENT_HISTORY if not
  G-OOS2: win_rate >= 0.40 OR payoff >= 1.0 → passes
  G-OOS3: liquidity >= 50 → passes
  G-OOS4: spread < 40% → passes
  G-OOS5: payoff >= 1.0 OR win_rate >= 0.60 → passes
  G-OOS6: pnl > -max_loss * 0.3 → passes (drawdown tolerable)
  G-OOS7: n >= 5 occurrences → passes
  G-OOS8: max_profit != inf AND max_loss > 0 → passes

Final classification logic:
  * If available_days < 5: INSUFFICIENT_HISTORY
  * Elif liquidity < 30: ILLIQUID_HISTORY
  * Elif max_profit == inf OR max_loss <= 0: OPTIONS_OOS_BLOCKED
  * Elif pnl < -max_loss * 0.3: OPTIONS_OOS_BLOCKED
  * Elif all G-OOS1-8 pass AND available_days >= 30 AND liquidity >= 50 AND payoff >= 1.0:
      OPTIONS_OOS_APPROVED_FOR_STUDY
  * Elif liquidity >= 30 AND (payoff >= 0.5 OR win_rate >= 0.3): OPTIONS_OOS_MONITOR_ONLY
  * Else: OPTIONS_OOS_BLOCKED

Decision levels:
  - PAPER_ONLY: < 5 dias ou classificação bloqueante
  - MANUAL_REVIEW_READY: >= 5 dias, estrutura válida
  - OPERATIONAL_READY: >= 30 dias, todos os gates pass
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from src.dashboard.data import _db_path


# ── Status constants ────────────────────────────────────────────────────────────

OOS_APPROVED = "OPTIONS_OOS_APPROVED_FOR_STUDY"
OOS_MONITOR = "OPTIONS_OOS_MONITOR_ONLY"
OOS_BLOCKED = "OPTIONS_OOS_BLOCKED"
INSUFFICIENT = "INSUFFICIENT_HISTORY"
ILLIQUID = "ILLIQUID_HISTORY"

ALL_STATUSES = [OOS_APPROVED, OOS_MONITOR, OOS_BLOCKED, INSUFFICIENT, ILLIQUID]

# Decision levels
DECISION_PAPER_ONLY = "PAPER_ONLY"
DECISION_MANUAL_REVIEW = "MANUAL_REVIEW_READY"
DECISION_OPERATIONAL = "OPERATIONAL_READY"


# ── Schema ─────────────────────────────────────────────────────────────────────

OOS_TABLE = "options_oos_classification"

OOS_COLUMNS = [
    "classification_id INTEGER PRIMARY KEY AUTOINCREMENT",
    "run_id TEXT NOT NULL",
    "run_date TEXT NOT NULL",
    "structure_type TEXT NOT NULL",
    "underlying TEXT NOT NULL",
    "oos_status TEXT",
    "train_window TEXT",
    "val_window TEXT",
    "test_window TEXT",
    "n_train INTEGER DEFAULT 0",
    "n_val INTEGER DEFAULT 0",
    "n_test INTEGER DEFAULT 0",
    "win_rate_train REAL",
    "win_rate_val REAL",
    "win_rate_test REAL",
    "avg_pnl_train REAL",
    "avg_pnl_val REAL",
    "avg_pnl_test REAL",
    "max_drawdown_train REAL",
    "liquidity_avg REAL",
    "spread_avg REAL",
    "iv_regime TEXT",
    "blocked_reasons TEXT",
    "passed_rules TEXT",
    "failed_rules TEXT",
    "confidence REAL DEFAULT 0.0",
    "notes TEXT",
    "created_at TEXT NOT NULL",
]


# ── Schema management ───────────────────────────────────────────────────────────

def ensure_oos_schema() -> None:
    """Creates or verifies options_oos_classification table."""
    db = _db_path()
    with sqlite3.connect(db) as con:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (OOS_TABLE,),
        )
        if cur.fetchone():
            return  # already exists

        cols_sql = ",\n  ".join(OOS_COLUMNS)
        con.execute(f"CREATE TABLE {OOS_TABLE} (\n  {cols_sql}\n)")
        con.execute(
            f"CREATE UNIQUE INDEX idx_oos_underlying_structure "
            f"ON {OOS_TABLE}(underlying, structure_type)"
        )
        con.commit()


# ── Data loading helpers ───────────────────────────────────────────────────────

def load_backtest_results(run_id: str | None = None) -> list[dict]:
    """Load backtest results from DB."""
    db = _db_path()
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        if run_id:
            cur = con.execute(
                "SELECT * FROM options_backtest_results WHERE run_id=?",
                (run_id,),
            )
        else:
            # get latest run
            cur = con.execute("""
                SELECT * FROM options_backtest_results
                WHERE run_id = (SELECT MAX(run_id) FROM options_backtest_results)
            """)
        return [dict(row) for row in cur.fetchall()]


def load_candidates() -> list[dict]:
    """Load option structure candidates."""
    db = _db_path()
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute("SELECT * FROM option_structure_candidates")
        return [dict(row) for row in cur.fetchall()]


def compute_available_days(results: list[dict]) -> int:
    """Compute distinct trading days in results."""
    dates = set(r["entry_date"] for r in results if r.get("entry_date"))
    return len(dates)


# ── G-OOS Rules ────────────────────────────────────────────────────────────────

def evaluate_goos_rules(
    results: list[dict],
    liquidity: float,
    iv_regime: str,
) -> tuple[dict[str, bool], dict[str, str]]:
    """
    Evaluate G-OOS rules 1-8.

    Returns:
        passed: dict rule_name -> passed (True/False)
        reasons: dict rule_name -> failure reason if not passed
    """
    passed = {}
    reasons = {}

    # G-OOS1: available_days >= 30
    avail = compute_available_days(results)
    g1_pass = avail >= 30
    passed["G-OOS1"] = g1_pass
    reasons["G-OOS1"] = "" if g1_pass else f"available_days={avail} < 30"

    # G-OOS2: win_rate >= 0.40 OR payoff >= 1.0
    wins = sum(1 for r in results if r.get("win") == 1)
    total = len(results) or 1
    win_rate = wins / total
    payoff = _compute_avg_payoff(results)
    g2_pass = win_rate >= 0.40 or payoff >= 1.0
    passed["G-OOS2"] = g2_pass
    reasons["G-OOS2"] = (
        "" if g2_pass else f"win_rate={win_rate:.2f} < 0.40 AND payoff={payoff:.2f} < 1.0"
    )

    # G-OOS3: liquidity >= 50
    g3_pass = liquidity >= 50
    passed["G-OOS3"] = g3_pass
    reasons["G-OOS3"] = "" if g3_pass else f"liquidity={liquidity:.1f} < 50"

    # G-OOS4: spread < 40%
    spreads = [r["spread_entry"] for r in results if r.get("spread_entry") is not None]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0
    g4_pass = avg_spread < 40.0
    passed["G-OOS4"] = g4_pass
    reasons["G-OOS4"] = (
        "" if g4_pass else f"avg_spread={avg_spread:.2f}% >= 40%"
    )

    # G-OOS5: payoff >= 1.0 OR win_rate >= 0.60
    g5_pass = payoff >= 1.0 or win_rate >= 0.60
    passed["G-OOS5"] = g5_pass
    reasons["G-OOS5"] = (
        "" if g5_pass else f"payoff={payoff:.2f} < 1.0 AND win_rate={win_rate:.2f} < 0.60"
    )

    # G-OOS6: pnl > -max_loss * 0.3
    pnls = [r["pnl_reais"] for r in results if r.get("pnl_reais") is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    max_losses = [r["max_loss"] for r in results if r.get("max_loss") is not None and r["max_loss"] > 0]
    max_loss_val = max(max_losses) if max_losses else 0.0
    g6_pass = max_loss_val == 0 or avg_pnl > -max_loss_val * 0.3
    passed["G-OOS6"] = g6_pass
    reasons["G-OOS6"] = (
        "" if g6_pass else f"avg_pnl={avg_pnl:.2f} <= -max_loss*0.3={-max_loss_val*0.3:.2f}"
    )

    # G-OOS7: n >= 5 occurrences
    g7_pass = len(results) >= 5
    passed["G-OOS7"] = g7_pass
    reasons["G-OOS7"] = "" if g7_pass else f"n={len(results)} < 5"

    # G-OOS8: max_profit != inf AND max_loss > 0
    max_profits = [r["max_profit"] for r in results if r.get("max_profit") is not None]
    max_profit = max(max_profits) if max_profits else 0.0
    max_loss_positive = max_loss_val > 0
    g8_pass = max_profit != float("inf") and max_loss_positive
    passed["G-OOS8"] = g8_pass
    reasons["G-OOS8"] = (
        "" if g8_pass else f"max_profit={max_profit} (inf={max_profit==float('inf')}) "
        f"OR max_loss={max_loss_val} <= 0"
    )

    return passed, reasons


def _compute_avg_payoff(results: list[dict]) -> float:
    """
    Compute REALIZED payoff ratio from historical simulation.

    payoff_realized = avg_win / abs(avg_loss), where:
      - avg_win  = mean of pnl_reais over wins   (pnl_reais > 0)
      - avg_loss = mean of pnl_reais over losses (pnl_reais < 0)

    Rationale: payoff must reflect actual historical distribution of outcomes,
    not the theoretical max_profit/max_loss from the option structure.
    The theoretical value is preserved as a separate metric (max_profit/max_loss)
    and used only for structural diagnostics, not for OOS performance gates.

    Rules applied:
      - If no losses at all  → apply conservative fallback (documented below)
      - If no wins at all   → payoff_realized = 0.0 (conservative)
      - If avg_loss == 0    → payoff_realized = 0.0
    """
    pnls = [r.get("pnl_reais") for r in results if r.get("pnl_reais") is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    if not losses:
        # No realized losses in simulation history.
        # Apply conservative fallback: use 0.5 * avg_win as the loss proxy
        # (equivalent to saying "on average we would have lost half a typical win")
        if wins:
            avg_win_val = sum(wins) / len(wins)
            conservative_loss_proxy = avg_win_val * 0.5  # 50% of avg_win as loss estimate
            if conservative_loss_proxy > 0:
                return avg_win_val / conservative_loss_proxy
        return 0.0

    avg_loss_val = sum(losses) / len(losses)  # negative number

    if not wins:
        # All outcomes were losses — no realized gains
        return 0.0

    avg_win_val = sum(wins) / len(wins)

    return avg_win_val / abs(avg_loss_val)


# ── Classification logic ────────────────────────────────────────────────────────

def classify_structure_oos(
    structure_type: str,
    backtest_results: list[dict],
    liquidity: float,
    iv_regime: str,
) -> dict[str, Any]:
    """
    Apply G-OOS rules and return classification dict.

    Args:
        structure_type: e.g. 'PUT_SPREAD', 'CALL_SPREAD'
        backtest_results: list of result dicts for this structure
        liquidity: average liquidity score
        iv_regime: regime label from results

    Returns classification dict with:
        status, passed_rules, failed_rules, blocked_reasons,
        confidence, notes, available_days, payoff, win_rate,
        train_window, val_window, test_window,
        n_train, n_val, n_test,
        win_rate_train, win_rate_val, win_rate_test,
        avg_pnl_train, avg_pnl_val, avg_pnl_test,
        max_drawdown_train, liquidity_avg, spread_avg, iv_regime_out
    """
    # Evaluate G-OOS rules
    passed, reasons = evaluate_goos_rules(backtest_results, liquidity, iv_regime)
    all_passed = all(passed.values())

    # Compute available days
    avail = compute_available_days(backtest_results)

    # Compute metrics
    wins = sum(1 for r in backtest_results if r.get("win") == 1)
    total = len(backtest_results) or 1
    win_rate = wins / total
    payoff = _compute_avg_payoff(backtest_results)
    spreads = [r["spread_entry"] for r in backtest_results if r.get("spread_entry") is not None]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0

    pnls = [r["pnl_reais"] for r in backtest_results if r.get("pnl_reais") is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    max_losses = [r["max_loss"] for r in backtest_results if r.get("max_loss") is not None and r["max_loss"] > 0]
    max_loss_val = max(max_losses) if max_losses else 0.0
    max_profits = [r["max_profit"] for r in backtest_results if r.get("max_profit") is not None]
    max_profit_val = max(max_profits) if max_profits else 0.0

    # Split into windows (even if minimal, document the windows)
    n = len(backtest_results)
    if n >= 10:
        # 60/20/20 split
        n_train = max(1, int(n * 0.6))
        n_val = max(1, int(n * 0.2))
        n_test = n - n_train - n_val
    elif n >= 3:
        n_train = max(1, n // 2)
        n_val = max(1, (n - n_train) // 2)
        n_test = n - n_train - n_val
    else:
        n_train = n
        n_val = 0
        n_test = 0

    sorted_results = sorted(backtest_results, key=lambda r: r.get("entry_date") or "")
    train_results = sorted_results[:n_train]
    val_results = sorted_results[n_train:n_train + n_val]
    test_results = sorted_results[n_train + n_val:]

    def window_metrics(results):
        if not results:
            return 0.0, 0.0, 0.0
        w = sum(1 for r in results if r.get("win") == 1) / max(len(results), 1)
        p = [r["pnl_reais"] for r in results if r.get("pnl_reais") is not None]
        avg = sum(p) / len(p) if p else 0.0
        max_dd = min(p) if p else 0.0
        return (
            w,
            avg,
            max_dd,
        )

    wr_train, pnl_train, dd_train = window_metrics(train_results)
    wr_val, pnl_val, dd_val = window_metrics(val_results)
    wr_test, pnl_test, dd_test = window_metrics(test_results)
    # spread_avg already computed above as avg_spread

    # Date windows (use actual dates from results)
    dates = sorted(set(r.get("entry_date") for r in backtest_results if r.get("entry_date")))
    if dates:
        train_win = f"{dates[0]} to {dates[min(n_train-1, len(dates)-1)]}" if n_train else "N/A"
        val_start = dates[min(n_train, len(dates)-1)] if n_val else "N/A"
        val_end = dates[min(n_train + n_val - 1, len(dates)-1)] if n_val else "N/A"
        val_win = f"{val_start} to {val_end}" if n_val else "N/A"
        test_start = dates[min(n_train + n_val, len(dates)-1)] if n_test else "N/A"
        test_end = dates[-1] if n_test else "N/A"
        test_win = f"{test_start} to {test_end}" if n_test else "N/A"
    else:
        train_win = val_win = test_win = "N/A"

    # Blocked reasons from rules
    blocked = [reasons[k] for k in sorted(reasons) if not passed[k] and reasons[k]]

    # Confidence: proportion of rules passed
    n_passed = sum(passed.values())
    confidence = n_passed / len(passed)

    # ── Final classification ──────────────────────────────────────────────────
    if avail < 5:
        status = INSUFFICIENT
        notes = (
            f"INSUFFICIENT_HISTORY: available_days={avail} < 5. "
            f"Com apenas {avail} dia(s) de dados históricos, não há base para "
            f"validação OOS. Estrutura requer pelo menos 5 dias de histórico."
        )
    elif liquidity < 30:
        status = ILLIQUID
        notes = (
            f"ILLIQUID_HISTORY: liquidity_avg={liquidity:.1f} < 30. "
            f"Spread médio de opções indica liquidez insuficiente para OOS."
        )
    elif max_profit_val == float("inf") or max_loss_val <= 0:
        status = OOS_BLOCKED
        blocked.append(
            f"max_profit=inf:{max_profit_val==float('inf')} OR max_loss={max_loss_val} <= 0"
        )
        notes = "OPTIONS_OOS_BLOCKED: max_profit/max_loss undefined or invalid."
    elif avg_pnl < -max_loss_val * 0.3:
        status = OOS_BLOCKED
        blocked.append(f"avg_pnl={avg_pnl:.2f} < -max_loss*0.3={-max_loss_val*0.3:.2f}")
        notes = "OPTIONS_OOS_BLOCKED: Drawdown exceeds 30% threshold."
    elif (
        all_passed
        and avail >= 30
        and liquidity >= 50
        and payoff >= 1.0
    ):
        status = OOS_APPROVED
        notes = (
            "OPTIONS_OOS_APPROVED_FOR_STUDY: All G-OOS rules passed, "
            f"avail_days={avail}>=30, liquidity={liquidity:.1f}>=50, payoff={payoff:.2f}>=1.0"
        )
    elif liquidity >= 30 and (payoff >= 0.5 or win_rate >= 0.3):
        status = OOS_MONITOR
        notes = (
            f"OPTIONS_OOS_MONITOR_ONLY: partial validation. "
            f"liquidity={liquidity:.1f}>=30, payoff={payoff:.2f}>=0.5 OR "
            f"win_rate={win_rate:.2f}>=0.3, but not all G-OOS rules passed."
        )
    else:
        status = OOS_BLOCKED
        notes = (
            f"OPTIONS_OOS_BLOCKED: G-OOS rules failed. "
            f"passed={n_passed}/{len(passed)}, avail_days={avail}, "
            f"liquidity={liquidity:.1f}, payoff={payoff:.2f}, win_rate={win_rate:.2f}"
        )

    return {
        "status": status,
        "passed_rules": ",".join(k for k, v in passed.items() if v),
        "failed_rules": ",".join(k for k, v in passed.items() if not v),
        "blocked_reasons": "; ".join(blocked) if blocked else "",
        "confidence": confidence,
        "notes": notes,
        # Metrics
        "available_days": avail,
        "win_rate": win_rate,
        "payoff": payoff,
        "avg_spread": avg_spread,
        "avg_pnl": avg_pnl,
        "max_loss": max_loss_val,
        "max_profit": max_profit_val,
        # Window splits
        "train_window": train_win,
        "val_window": val_win,
        "test_window": test_win,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "win_rate_train": wr_train,
        "win_rate_val": wr_val,
        "win_rate_test": wr_test,
        "avg_pnl_train": pnl_train,
        "avg_pnl_val": pnl_val,
        "avg_pnl_test": pnl_test,
        "max_drawdown_train": dd_train,
        "liquidity_avg": liquidity,
        "spread_avg": avg_spread,
        "iv_regime": iv_regime or "UNKNOWN",
    }


# ── Main classification function ──────────────────────────────────────────────

def run_walk_forward_classification(run_id: str | None = None) -> dict[str, Any]:
    """
    Main entry point: classify all structure types from backtest results.

    Args:
        run_id: optional specific run_id, else uses latest

    Returns summary dict:
        {
            "run_id": str,
            "classified_at": str,
            "by_structure": {structure_type: classification},
            "oos_totals": {status: count},
            "decision": PAPER_ONLY|MANUAL_REVIEW_READY|OPERATIONAL_READY,
            "decision_reason": str,
            "data_limitation": str,
            "total_structures": int,
        }
    """
    ensure_oos_schema()

    # Load data
    results = load_backtest_results(run_id)
    candidates = load_candidates()

    if not results:
        return {
            "run_id": run_id or "NONE",
            "classified_at": datetime.now().isoformat(),
            "by_structure": {},
            "oos_totals": {},
            "decision": DECISION_PAPER_ONLY,
            "decision_reason": "Nenhum resultado de backtest encontrado.",
            "data_limitation": "Sem dados disponíveis para classificação.",
            "total_structures": 0,
        }

    # Get run_id from results if not provided
    actual_run_id = run_id or results[0]["run_id"]
    run_date = results[0].get("run_date") or datetime.now().strftime("%Y-%m-%d")

    # Group results by structure_type + underlying
    grouped: dict[str, list[dict]] = {}
    for r in results:
        key = f"{r['structure_type']}:{r['underlying']}"
        grouped.setdefault(key, []).append(r)

    by_structure: dict[str, dict] = {}
    status_counts: dict[str, int] = {s: 0 for s in ALL_STATUSES}

    # Get unique structure types from candidates
    structure_types = set(c["structure_type"] for c in candidates)

    for stype in sorted(structure_types):
        # Collect results for this structure type (any underlying)
        st_results = [r for k, rs in grouped.items() for r in rs if k.startswith(f"{stype}:")]

        if not st_results:
            # No backtest results for this structure type
            classification = classify_structure_oos(stype, [], 0.0, "UNKNOWN")
            classification["status"] = INSUFFICIENT
            classification["notes"] = f"{stype}: Sem resultados de backtest disponíveis. INSUFFICIENT_HISTORY."
            classification["confidence"] = 0.0
        else:
            # Aggregate liquidity from results
            liq_scores = [r["liquidity_score"] for r in st_results if r.get("liquidity_score") is not None]
            avg_liquidity = sum(liq_scores) / len(liq_scores) if liq_scores else 0.0
            iv_regime = st_results[0].get("regime") or "UNKNOWN"

            classification = classify_structure_oos(stype, st_results, avg_liquidity, iv_regime)

        # Persist to DB
        persist_classification(
            run_id=actual_run_id,
            run_date=run_date,
            structure_type=stype,
            underlying=st_results[0]["underlying"] if st_results else "N/A",
            classification=classification,
        )

        by_structure[stype] = classification
        status_counts[classification["status"]] = status_counts.get(classification["status"], 0) + 1

    # Decision logic (uses shared helpers for consistency)
    avail_days = max(compute_available_days(results), 1)
    decision = _compute_decision(status_counts, avail_days)
    decision_reason = _compute_decision_reason(
        status_counts, avail_days,
        approved_study=[st for st, cls in by_structure.items() if cls["status"] == OOS_APPROVED],
        monitor_only=[st for st, cls in by_structure.items() if cls["status"] == OOS_MONITOR],
        blocked=[st for st, cls in by_structure.items() if cls["status"] == OOS_BLOCKED],
        insufficient=[st for st, cls in by_structure.items() if cls["status"] == INSUFFICIENT],
    )

    data_limitation = (
        f"Dados de backtest disponíveis: apenas {avail_days} dia(s) "
        f"(mais recente: {results[0].get('entry_date') if results else 'N/A'}). "
        f"Validação OOS com dados mínimos é inherentemente incerta. "
        f"Todos os resultados devem ser tratados como preliminares."
    )

    summary = {
        "run_id": actual_run_id,
        "classified_at": datetime.now().isoformat(),
        "by_structure": by_structure,
        "oos_totals": {k: v for k, v in status_counts.items() if v > 0},
        "decision": decision,
        "decision_reason": decision_reason,
        "data_limitation": data_limitation,
        "total_structures": len(by_structure),
        "available_days": avail_days,
    }

    return summary


def persist_classification(
    run_id: str,
    run_date: str,
    structure_type: str,
    underlying: str,
    classification: dict[str, Any],
) -> None:
    """Insert or replace a classification record."""
    db = _db_path()
    now = datetime.now().isoformat(timespec="seconds")
    with sqlite3.connect(db) as con:
        con.execute(f"""
            INSERT OR REPLACE INTO {OOS_TABLE} (
                run_id, run_date, structure_type, underlying, oos_status,
                train_window, val_window, test_window,
                n_train, n_val, n_test,
                win_rate_train, win_rate_val, win_rate_test,
                avg_pnl_train, avg_pnl_val, avg_pnl_test,
                max_drawdown_train, liquidity_avg, spread_avg, iv_regime,
                blocked_reasons, passed_rules, failed_rules, confidence, notes,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            run_date,
            structure_type,
            underlying,
            classification["status"],
            classification.get("train_window"),
            classification.get("val_window"),
            classification.get("test_window"),
            classification.get("n_train", 0),
            classification.get("n_val", 0),
            classification.get("n_test", 0),
            classification.get("win_rate_train"),
            classification.get("win_rate_val"),
            classification.get("win_rate_test"),
            classification.get("avg_pnl_train"),
            classification.get("avg_pnl_val"),
            classification.get("avg_pnl_test"),
            classification.get("max_drawdown_train"),
            classification.get("liquidity_avg"),
            classification.get("spread_avg"),
            classification.get("iv_regime"),
            classification.get("blocked_reasons"),
            classification.get("passed_rules"),
            classification.get("failed_rules"),
            classification.get("confidence", 0.0),
            classification.get("notes"),
            now,
        ))


# ── Query functions ─────────────────────────────────────────────────────────────

def get_oos_classification(ticker: str, structure_type: str | None = None) -> list[dict]:
    """
    Get OOS classification for a ticker.

    Args:
        ticker: underlying ticker (e.g. 'PETR')
        structure_type: optional filter by structure type

    Returns:
        List of classification dicts, newest first
    """
    ensure_oos_schema()
    db = _db_path()
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        if structure_type:
            cur = con.execute(
                f"SELECT * FROM {OOS_TABLE} WHERE underlying=? AND structure_type=? ORDER BY created_at DESC",
                (ticker, structure_type),
            )
        else:
            cur = con.execute(
                f"SELECT * FROM {OOS_TABLE} WHERE underlying=? ORDER BY created_at DESC",
                (ticker,),
            )
        return [dict(row) for row in cur.fetchall()]


def get_oos_dashboard() -> dict[str, Any]:
    """
    Return dashboard summary of OOS classifications.

    Returns:
        {
            "by_structure": {structure_type: latest_classification},
            "oos_totals": {status: count},
            "decision": PAPER_ONLY|MANUAL_REVIEW_READY|OPERATIONAL_READY,
            "decision_reason": str,
            "data_limitation": str,
            "total_candidates": int,
            "available_days": int,
        }
    """
    ensure_oos_schema()
    db = _db_path()

    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row

        # Get all classifications
        cur = con.execute(f"SELECT * FROM {OOS_TABLE} ORDER BY created_at DESC")
        all_classifications = [dict(row) for row in cur.fetchall()]

        if not all_classifications:
            # No classifications yet — run classification
            result = run_walk_forward_classification()
            # Re-read
            cur = con.execute(f"SELECT * FROM {OOS_TABLE} ORDER BY created_at DESC")
            all_classifications = [dict(row) for row in cur.fetchall()]

            return {
                "by_structure": result["by_structure"],
                "oos_totals": result["oos_totals"],
                "decision": result["decision"],
                "decision_reason": result["decision_reason"],
                "data_limitation": result["data_limitation"],
                "total_candidates": result["total_structures"],
                "available_days": result.get("available_days", 0),
            }

        # Build by_structure (latest per structure_type)
        by_structure: dict[str, dict] = {}
        seen_structures = set()
        for cls in all_classifications:
            st = cls["structure_type"]
            if st not in seen_structures:
                by_structure[st] = cls
                seen_structures.add(st)

        # Count totals (from latest classifications only)
        oos_totals: dict[str, int] = {s: 0 for s in ALL_STATUSES}
        for cls in by_structure.values():
            status = cls["oos_status"]
            oos_totals[status] = oos_totals.get(status, 0) + 1

        # Get available days from backtest results
        backtest_results = load_backtest_results()
        avail_days = compute_available_days(backtest_results)

        # Decision logic (uses shared helpers for consistency with _compute_decision)
        total_structures = len(by_structure)
        insufficient_list = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == INSUFFICIENT
        ]
        blocked_list = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == OOS_BLOCKED
        ]

        decision = _compute_decision(oos_totals, avail_days)
        decision_reason = _compute_decision_reason(
            oos_totals, avail_days,
            approved_study=[st for st, cls in by_structure.items() if cls.get("oos_status") == OOS_APPROVED],
            monitor_only=[st for st, cls in by_structure.items() if cls.get("oos_status") == OOS_MONITOR],
            blocked=blocked_list,
            insufficient=insufficient_list,
        )

        data_limitation = (
            f"Dados disponíveis: apenas {avail_days} dia(s) de histórico de cotahist_daily. "
            f"Classificações OOS são preliminares e estão sujeitas a revisão conforme mais dados "
            f"se tornem disponíveis. Nenhuma decisão operacional deve ser tomada com base "
            f"exclusivamente nestes resultados."
        )

        return {
            "by_structure": by_structure,
            "oos_totals": {k: v for k, v in oos_totals.items() if v > 0},
            "decision": decision,
            "decision_reason": decision_reason,
            "data_limitation": data_limitation,
            "total_candidates": total_structures,
            "available_days": avail_days,
        }

def _compute_decision(
    oos_totals: dict[str, int],
    avail_days: int,
) -> str:
    """
    Compute decision level from OOS classification totals.

    Rules (in priority order):
      1. INSUFFICIENT majority → PAPER_ONLY
      2. BLOCKED majority → PAPER_ONLY
      3. avail_days < 5 → PAPER_ONLY
      4. APPROVED_FOR_STUDY > 0 AND avail_days >= 30 → OPERATIONAL_READY
         (all G-OOS rules passed; governance confirmed)
      5. otherwise → MANUAL_REVIEW_READY
         (MONITOR_ONLY structures exist but no full G-OOS approval;
          human review required before any operational use)

    IMPORTANT: MONITOR_ONLY with 30 aggregate days does NOT qualify for
    OPERATIONAL_READY. OPERATIONAL_READY requires APPROVED_FOR_STUDY == true
    for at least one structure. Rules are not relaxed based on aggregate
    data alone — individual structure metrics are what the G-OOS gates protect.
    """
    approved = oos_totals.get(OOS_APPROVED, 0)
    blocked = oos_totals.get(OOS_BLOCKED, 0)
    insufficient = oos_totals.get(INSUFFICIENT, 0)
    total = sum(oos_totals.values()) or 1

    if insufficient >= total:
        return DECISION_PAPER_ONLY
    elif blocked >= total:
        return DECISION_PAPER_ONLY
    elif avail_days < 5:
        return DECISION_PAPER_ONLY
    elif approved > 0 and avail_days >= 30:
        return DECISION_OPERATIONAL
    else:
        return DECISION_MANUAL_REVIEW


def _compute_decision_reason(
    oos_totals: dict[str, int],
    avail_days: int,
    approved_study: list[str],
    monitor_only: list[str],
    blocked: list[str],
    insufficient: list[str],
) -> str:
    """
    Compute human-readable decision reason.

    Mirrors _compute_decision() logic so the reason matches the actual
    decision. Key constraint: MONITOR_ONLY alone does NOT qualify for
    OPERATIONAL_READY — at least one structure must be APPROVED_FOR_STUDY.
    """
    approved = oos_totals.get(OOS_APPROVED, 0)
    blocked_cnt = oos_totals.get(OOS_BLOCKED, 0)
    monitor = oos_totals.get(OOS_MONITOR, 0)
    insufficient_cnt = oos_totals.get(INSUFFICIENT, 0)
    total = sum(oos_totals.values()) or 1

    if insufficient_cnt >= total:
        return (
            f"Todas as {total} estrutura(s) classificadas como INSUFFICIENT_HISTORY. "
            f"Apenas {avail_days} dia(s) de dados disponíveis. "
            f"Usar PAPER_ONLY até que mais dados históricos estejam disponíveis."
        )
    elif blocked_cnt >= total:
        return (
            f"Todas as {total} estrutura(s) bloqueadas. "
            f"Nenhuma estrutura passou nos gates G-OOS. "
            f"Usar PAPER_ONLY até que mais dados históricos estejam disponíveis."
        )
    elif avail_days < 5:
        return (
            f"Dados insuficientes: apenas {avail_days} dia(s). "
            f"Requer >= 5 dias para classificação OOS. "
            f"Resultado: PAPER_ONLY."
        )
    elif approved > 0 and avail_days >= 30:
        return (
            f"{approved} estrutura(s) APPROVED_FOR_STUDY com {avail_days} dias. "
            f"Todos os gates G-OOS passados. "
            f"Decisão: OPERATIONAL_READY — uso operacional com monitoramento."
        )
    else:
        # MANUAL_REVIEW_READY: no APPROVED structures
        return (
            f"{approved} APPROVED, {monitor} MONITOR_ONLY, {blocked_cnt} BLOCKED, "
            f"{insufficient_cnt} INSUFFICIENT. {total} estruturas classificadas. "
            f"Sem estruturas APPROVED_FOR_STUDY — revisão manual obrigatória "
            f"antes de qualquer uso operacional."
        )


def get_options_system_health() -> dict[str, Any]:
    """
    High-level options system health dashboard.

    Returns:
        {
            "ok": bool,
            "data_available": bool,
            "chain_snapshots": int,
            "greeks_snapshots": int,
            "historical_dates": int,
            "candidates_total": int,
            "candidates_simulated": int,
            "backtest_rows": int,
            "backtest_run_id": str | None,
            "oos_totals": dict[status: count],
            "approved_for_study": list[str],   # structure types
            "monitor_only": list[str],
            "blocked": list[str],
            "insufficient_history": list[str],
            "illiquid_history": list[str],
            "decision": PAPER_ONLY|MANUAL_REVIEW_READY|OPERATIONAL_READY,
            "decision_reason": str,
            "data_limitation": str,
            "critical_issues": list[str],
        }
    """
    from src.dashboard.data import _db_path

    db = _db_path()
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row

        # ── Data availability counts ─────────────────────────────────────
        chain_cnt = con.execute(
            "SELECT COUNT(*) FROM options_chain_snapshots"
        ).fetchone()[0]
        chain_dates = con.execute(
            "SELECT COUNT(DISTINCT trade_date) FROM options_chain_snapshots"
        ).fetchone()[0]
        greeks_cnt = con.execute(
            "SELECT COUNT(*) FROM options_greeks_snapshot"
        ).fetchone()[0]
        greeks_dates = con.execute(
            "SELECT COUNT(DISTINCT trade_date) FROM options_greeks_snapshot"
        ).fetchone()[0]

        cand_total = con.execute(
            "SELECT COUNT(*) FROM option_structure_candidates "
            "WHERE candidate_status NOT LIKE 'BLOQUEADO%'"
        ).fetchone()[0]

        # ── Latest backtest run (prefer most entry dates, then most recent) ──
        latest_run = con.execute("""
            SELECT run_id, COUNT(DISTINCT entry_date) as n_dates
            FROM options_backtest_results
            GROUP BY run_id
            ORDER BY n_dates DESC, run_id DESC
            LIMIT 1
        """).fetchone()

        backtest_rows = 0
        cand_simulated = 0
        bt_dates = 0
        if latest_run:
            run_id, bt_dates = latest_run
            row = con.execute("""
                SELECT COUNT(*), COUNT(DISTINCT candidate_id)
                FROM options_backtest_results WHERE run_id=?
            """, (run_id,)).fetchone()
            backtest_rows = row[0]
            cand_simulated = row[1]
        else:
            run_id = None

        # ── OOS classification from latest run ────────────────────────────
        # Get latest classification per structure_type directly from DB
        try:
            cur = con.execute("""
                SELECT structure_type, oos_status, confidence, liquidity_avg,
                       win_rate_train, win_rate_val, win_rate_test,
                       avg_pnl_train, avg_pnl_val, avg_pnl_test,
                       max_drawdown_train, spread_avg, iv_regime,
                       passed_rules, failed_rules, blocked_reasons, notes,
                       train_window, val_window, test_window,
                       n_train, n_val, n_test
                FROM options_oos_classification o1
                WHERE rowid = (
                    SELECT MAX(rowid) FROM options_oos_classification o2
                    WHERE o2.structure_type = o1.structure_type
                )
                ORDER BY structure_type
            """)
            raw_by_structure = [dict(row) for row in cur.fetchall()]
        except Exception:
            raw_by_structure = []

        by_structure: dict[str, dict] = {r["structure_type"]: r for r in raw_by_structure}

        oos_totals: dict[str, int] = {}
        for r in raw_by_structure:
            status = r.get("oos_status", "UNKNOWN")
            oos_totals[status] = oos_totals.get(status, 0) + 1

        approved_study = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == OOS_APPROVED
        ]
        monitor_only = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == OOS_MONITOR
        ]
        blocked = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == OOS_BLOCKED
        ]
        insufficient = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == INSUFFICIENT
        ]
        illiquid = [
            st for st, cls in by_structure.items()
            if cls.get("oos_status") == ILLIQUID
        ]

        # ── Critical issues ────────────────────────────────────────────────
        issues: list[str] = []
        avail_days = bt_dates

        if chain_cnt == 0:
            issues.append("NENHUMA chain snapshot — backfill não executado")
        elif chain_dates < 30:
            issues.append(f"Apenas {chain_dates} datas em chain_snapshots (requer >= 30 para G-OOS1)")
        if backtest_rows == 0:
            issues.append("NENHUMA linha de backtest — run_options_backtest_historical.py falhou")
        if not latest_run:
            issues.append("Nenhum run de backtest encontrado")
        if insufficient:
            issues.append(f"Estruturas INSUFFICIENT_HISTORY: {', '.join(insufficient)}")
        if illiquid:
            issues.append(f"Estruturas ILLIQUID_HISTORY: {', '.join(illiquid)}")
        if greeks_cnt == 0:
            issues.append("NENHUMA snapshot de gregas — Greeks não populados")
        if not issues:
            issues.append("Nenhum problema crítico detectado")

        return {
            "ok": True,
            "data_available": chain_cnt > 0 and backtest_rows > 0,
            "chain_snapshots": chain_cnt,
            "chain_dates": chain_dates,
            "greeks_snapshots": greeks_cnt,
            "greeks_dates": greeks_dates,
            "historical_dates": bt_dates,
            "candidates_total": cand_total,
            "candidates_simulated": cand_simulated,
            "backtest_rows": backtest_rows,
            "backtest_run_id": run_id,
            "oos_totals": oos_totals,
            "by_structure": by_structure,
            "approved_for_study": approved_study,
            "monitor_only": monitor_only,
            "blocked": blocked,
            "insufficient_history": insufficient,
            "illiquid_history": illiquid,
            "decision": _compute_decision(oos_totals, bt_dates),
            "decision_reason": _compute_decision_reason(oos_totals, bt_dates, approved_study, monitor_only, blocked, insufficient),
            "data_limitation": (
                f"Dados disponíveis: {bt_dates} dia(s) de backtest histórico. "
                f"Validação OOS com {chain_dates} datas em chain_snapshots e {greeks_dates} datas em greeks. "
                f"Classificações são preliminares e sujeitas a revisão conforme mais dados se tornem disponíveis."
            ),
            "critical_issues": issues,
        }