#!/usr/bin/env python3
"""
Options OOS Validator Runner — M010.5 S02 T02

Re-runs OOS classification with historical backtest data.
Reads: options_backtest_results (historical run)
       option_structure_candidates
Writes: options_oos_classification
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
sys.path.insert(0, str(ROOT))

from src.dashboard.data import _db_path

OOS_APPROVED = "OPTIONS_OOS_APPROVED_FOR_STUDY"
OOS_MONITOR = "OPTIONS_OOS_MONITOR_ONLY"
OOS_BLOCKED = "OPTIONS_OOS_BLOCKED"
INSUFFICIENT = "INSUFFICIENT_HISTORY"
ILLIQUID = "ILLIQUID_HISTORY"


def _db() -> Path:
    return _db_path()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_available_days(results: list[dict]) -> int:
    dates = set(r.get("entry_date") for r in results if r.get("entry_date"))
    return len(dates)


def compute_avg_payoff(results: list[dict]) -> float:
    payoffs = []
    for r in results:
        ml = r.get("max_loss") or 0
        mp = r.get("max_profit") or 0
        if ml < 0:
            payoffs.append(abs(mp / ml) if ml != 0 else 0.0)
    return sum(payoffs) / len(payoffs) if payoffs else 0.0


def evaluate_goos_rules(results: list[dict], liquidity: float):
    passed = {}
    reasons = {}

    avail = compute_available_days(results)
    g1_pass = avail >= 30
    passed["G-OOS1"] = g1_pass
    reasons["G-OOS1"] = "" if g1_pass else f"available_days={avail} < 30"

    wins = sum(1 for r in results if r.get("win") == 1)
    total = len(results) or 1
    win_rate = wins / total
    payoff = compute_avg_payoff(results)

    g2_pass = win_rate >= 0.40 or payoff >= 1.0
    passed["G-OOS2"] = g2_pass
    reasons["G-OOS2"] = "" if g2_pass else f"win_rate={win_rate:.2f}<0.40 AND payoff={payoff:.2f}<1.0"

    g3_pass = liquidity >= 50
    passed["G-OOS3"] = g3_pass
    reasons["G-OOS3"] = "" if g3_pass else f"liquidity={liquidity:.1f}<50"

    spreads = [r["spread_entry"] for r in results if r.get("spread_entry") is not None]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0
    g4_pass = avg_spread < 40.0
    passed["G-OOS4"] = g4_pass
    reasons["G-OOS4"] = "" if g4_pass else f"avg_spread={avg_spread:.2f}%>=40%"

    g5_pass = payoff >= 1.0 or win_rate >= 0.60
    passed["G-OOS5"] = g5_pass
    reasons["G-OOS5"] = "" if g5_pass else f"payoff={payoff:.2f}<1.0 AND win_rate={win_rate:.2f}<0.60"

    pnls = [r["pnl_reais"] for r in results if r.get("pnl_reais") is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
    max_losses = [r["max_loss"] for r in results if r.get("max_loss") is not None and r["max_loss"] > 0]
    max_loss_val = max(max_losses) if max_losses else 0.0
    g6_pass = max_loss_val == 0 or avg_pnl > -max_loss_val * 0.3
    passed["G-OOS6"] = g6_pass
    reasons["G-OOS6"] = "" if g6_pass else f"avg_pnl={avg_pnl:.2f}<=-max_loss*0.3={-max_loss_val*0.3:.2f}"

    g7_pass = len(results) >= 5
    passed["G-OOS7"] = g7_pass
    reasons["G-OOS7"] = "" if g7_pass else f"n={len(results)}<5"

    max_profits = [r["max_profit"] for r in results if r.get("max_profit") is not None]
    max_profit_val = max(max_profits) if max_profits else 0.0
    g8_pass = max_profit_val != float("inf") and max_loss_val > 0
    passed["G-OOS8"] = g8_pass
    reasons["G-OOS8"] = "" if g8_pass else f"max_profit=inf:{max_profit_val==float('inf')} OR max_loss={max_loss_val}<=0"

    return passed, reasons


def classify_structure(results: list[dict], liquidity: float, iv_regime: str) -> dict:
    avail = compute_available_days(results)
    wins = sum(1 for r in results if r.get("win") == 1)
    total = len(results) or 1
    win_rate = wins / total
    payoff = compute_avg_payoff(results)

    spreads = [r["spread_entry"] for r in results if r.get("spread_entry") is not None]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0
    pnls = [r["pnl_reais"] for r in results if r.get("pnl_reais") is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    max_losses = [r["max_loss"] for r in results if r.get("max_loss") is not None and r["max_loss"] > 0]
    max_loss_val = max(max_losses) if max_losses else 0.0
    max_profits = [r["max_profit"] for r in results if r.get("max_profit") is not None]
    max_profit_val = max(max_profits) if max_profits else 0.0

    passed, reasons = evaluate_goos_rules(results, liquidity)

    # Windows
    n = len(results)
    if n >= 10:
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

    sorted_results = sorted(results, key=lambda r: r.get("entry_date") or "")
    train_results = sorted_results[:n_train]
    val_results = sorted_results[n_train:n_train + n_val]
    test_results = sorted_results[n_train + n_val:]

    def window_metrics(res):
        if not res:
            return 0.0, 0.0, 0.0
        wr = sum(1 for r in res if r.get("win") == 1) / max(len(res), 1)
        pnl_list = [r["pnl_reais"] for r in res if r.get("pnl_reais") is not None]
        avg = sum(pnl_list) / len(pnl_list) if pnl_list else 0.0
        dd = min(pnl_list) if pnl_list else 0.0
        return wr, avg, dd

    wr_tr, pn_tr, dd_tr = window_metrics(train_results)
    wr_vl, pn_vl, dd_vl = window_metrics(val_results)
    wr_ts, pn_ts, dd_ts = window_metrics(test_results)

    dates = sorted(set(r.get("entry_date") for r in results if r.get("entry_date")))
    if dates and n_train > 0:
        train_win = f"{dates[0]} to {dates[min(n_train-1, len(dates)-1)]}"
    else:
        train_win = "N/A"
    val_win = (f"{dates[min(n_train, len(dates)-1)]} to {dates[min(n_train+n_val-1, len(dates)-1)]}"
               if n_val and dates else "N/A")
    test_win = (f"{dates[min(n_train+n_val, len(dates)-1)]} to {dates[-1]}"
                if n_test and dates else "N/A")

    blocked = [reasons[k] for k in sorted(reasons) if not passed[k] and reasons[k]]
    passed_list = [k for k in sorted(passed) if passed[k]]
    confidence = sum(passed.values()) / len(passed)

    # Final status
    if avail < 5:
        status = INSUFFICIENT
        notes = f"INSUFFICIENT_HISTORY: {avail} days < 5"
    elif liquidity < 30:
        status = ILLIQUID
        notes = f"ILLIQUID_HISTORY: avg_liquidity={liquidity:.1f} < 30"
    elif max_profit_val == float("inf") or max_loss_val <= 0:
        status = OOS_BLOCKED
        blocked.append(f"max_profit=inf:{max_profit_val==float('inf')} OR max_loss={max_loss_val}<=0")
        notes = "OPTIONS_OOS_BLOCKED: max_profit/max_loss invalid"
    elif avg_pnl < -max_loss_val * 0.3:
        status = OOS_BLOCKED
        blocked.append(f"avg_pnl={avg_pnl:.2f} < -max_loss*0.3={-max_loss_val*0.3:.2f}")
        notes = "OPTIONS_OOS_BLOCKED: drawdown exceeds threshold"
    elif avail >= 30 and liquidity >= 50 and payoff >= 1.0:
        status = OOS_APPROVED
        notes = f"OPTIONS_OOS_APPROVED_FOR_STUDY: {avail} days, liq={liquidity:.1f}, payoff={payoff:.2f}"
    elif liquidity >= 30 and (payoff >= 0.5 or win_rate >= 0.30):
        status = OOS_MONITOR
        notes = f"OPTIONS_OOS_MONITOR_ONLY: {avail} days, liq={liquidity:.1f}, payoff={payoff:.2f}, win_rate={win_rate:.1%}"
    else:
        status = OOS_BLOCKED
        notes = f"OPTIONS_OOS_BLOCKED: avail={avail}, liq={liquidity:.1f}, payoff={payoff:.2f}"

    return {
        "status": status,
        "avail": avail,
        "win_rate": round(win_rate, 4),
        "payoff": round(payoff, 4),
        "liquidity_avg": round(liquidity, 1),
        "spread_avg": round(avg_spread, 2),
        "iv_regime": iv_regime,
        "max_loss": round(max_loss_val, 2),
        "max_profit": round(max_profit_val, 2),
        "avg_pnl": round(avg_pnl, 2),
        "blocked": blocked,
        "passed": passed_list,
        "failed": [k for k in sorted(reasons) if not passed[k]],
        "confidence": round(confidence, 3),
        "notes": notes,
        "train_win": train_win,
        "val_win": val_win,
        "test_win": test_win,
        "n_train": n_train, "n_val": n_val, "n_test": n_test,
        "wr_train": round(wr_tr, 4), "wr_val": round(wr_vl, 4), "wr_test": round(wr_ts, 4),
        "pnl_train": round(pn_tr, 2), "pnl_val": round(pn_vl, 2), "pnl_test": round(pn_ts, 2),
        "dd_train": round(dd_tr, 2), "dd_val": round(dd_vl, 2), "dd_test": round(dd_ts, 2),
    }


def run_oos_validation(run_id: str, backtest_run_id: str) -> dict:
    """Main OOS validation loop."""
    db = _db()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row

    # Load candidates
    cands = conn.execute("""
        SELECT id, underlying, structure_type, maturity_date,
               liquidity_score, governance_status, legs_json
        FROM option_structure_candidates
        WHERE candidate_status NOT LIKE 'BLOQUEADO%'
    """).fetchall()

    # Load backtest results for the historical run
    btresults = conn.execute("""
        SELECT * FROM options_backtest_results
        WHERE run_id = ?
    """, (backtest_run_id,)).fetchall()

    # Convert to dict keyed by candidate_id
    bt_by_cand = {}
    for r in btresults:
        cid = r["candidate_id"]
        if cid not in bt_by_cand:
            bt_by_cand[cid] = []
        bt_by_cand[cid].append(dict(r))

    # Clear old OOS classifications for this run
    conn.execute("DELETE FROM options_oos_classification WHERE run_id = ?", (run_id,))

    status_counts = {OOS_APPROVED: 0, OOS_MONITOR: 0, OOS_BLOCKED: 0,
                     INSUFFICIENT: 0, ILLIQUID: 0}
    structure_results = []

    now = _now()

    for cand in cands:
        cid = cand["id"]
        underlying = cand["underlying"]
        structure_type = cand["structure_type"]
        liquidity = float(cand["liquidity_score"] or 0)

        results = bt_by_cand.get(cid, [])
        iv_regime = "NEUTRAL_IV"  # default

        if not results:
            # No backtest data for this candidate
            status = INSUFFICIENT
            classification = {
                "status": status,
                "avail": 0, "win_rate": 0.0, "payoff": 0.0,
                "liquidity_avg": liquidity, "spread_avg": 0.0,
                "iv_regime": iv_regime, "max_loss": 0.0, "max_profit": 0.0,
                "avg_pnl": 0.0, "blocked": [], "passed": [], "failed": [],
                "confidence": 0.0, "notes": "No backtest data",
                "train_win": "N/A", "val_win": "N/A", "test_win": "N/A",
                "n_train": 0, "n_val": 0, "n_test": 0,
                "wr_train": 0.0, "wr_val": 0.0, "wr_test": 0.0,
                "pnl_train": 0.0, "pnl_val": 0.0, "pnl_test": 0.0,
                "dd_train": 0.0, "dd_val": 0.0, "dd_test": 0.0,
            }
        else:
            classification = classify_structure(results, liquidity, iv_regime)
            status = classification["status"]

        status_counts[status] += 1

        conn.execute("""
            INSERT INTO options_oos_classification (
                run_id, run_date, structure_type, underlying,
                oos_status, train_window, val_window, test_window,
                n_train, n_val, n_test,
                win_rate_train, win_rate_val, win_rate_test,
                avg_pnl_train, avg_pnl_val, avg_pnl_test,
                max_drawdown_train,
                liquidity_avg, spread_avg, iv_regime,
                blocked_reasons, passed_rules, failed_rules,
                confidence, notes, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            run_id, now[:10],
            structure_type, underlying,
            status,
            classification["train_win"],
            classification["val_win"],
            classification["test_win"],
            classification["n_train"], classification["n_val"], classification["n_test"],
            classification["wr_train"], classification["wr_val"], classification["wr_test"],
            classification["pnl_train"], classification["pnl_val"], classification["pnl_test"],
            classification["dd_train"],
            classification["liquidity_avg"],
            classification["spread_avg"],
            classification["iv_regime"],
            json.dumps(classification["blocked"]),
            json.dumps(classification["passed"]),
            json.dumps(classification["failed"]),
            classification["confidence"],
            classification["notes"],
            now,
        ))

        structure_results.append({
            "structure_type": structure_type,
            "underlying": underlying,
            "status": status,
            "avail": classification["avail"],
            "win_rate": classification["win_rate"],
            "payoff": classification["payoff"],
            "liquidity": classification["liquidity_avg"],
            "confidence": classification["confidence"],
        })

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "run_id": run_id,
        "backtest_run_id": backtest_run_id,
        "candidates": len(cands),
        "status_counts": status_counts,
        "structures": structure_results,
    }


def main():
    # Get the most recent backtest run
    db = _db()
    conn = sqlite3.connect(str(db))
    cur = conn.execute("""
        SELECT run_id, run_date, COUNT(*) as cnt
        FROM options_backtest_results
        GROUP BY run_id
        ORDER BY run_date DESC, run_id DESC
        LIMIT 5
    """)
    runs = cur.fetchall()
    conn.close()

    print("Available backtest runs:")
    for r in runs:
        print(f"  {r[0]} | {r[1]} | {r[2]} rows")

    # Use most recent
    if not runs:
        print("ERROR: No backtest runs found")
        return

    latest_bt_run = runs[0][0]
    oos_run_id = f"OOS_HIST_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n{'='*70}")
    print("  Options OOS Validator Runner — M010.5 S02 T02")
    print(f"  OOS Run: {oos_run_id}")
    print(f"  Backtest Run: {latest_bt_run}")
    print(f"{'='*70}")

    result = run_oos_validation(oos_run_id, latest_bt_run)

    print(f"\nOOS Results:")
    print(f"  Candidates: {result['candidates']}")
    print(f"  Status Counts:")
    for status, count in result["status_counts"].items():
        print(f"    {status}: {count}")

    print("\n  By structure:")
    for s in result["structures"]:
        print(f"    {s['underlying']}/{s['structure_type']}: {s['status']} | "
              f"days={s['avail']} | win={s['win_rate']:.0%} | "
              f"payoff={s['payoff']:.2f} | liq={s['liquidity']:.1f} | "
              f"conf={s['confidence']:.0%}")

    print(f"\n[OK] OOS validation complete: {oos_run_id}")


if __name__ == "__main__":
    main()