#!/usr/bin/env python3
"""
Options Historical Backtest Runner — M010.5 S02 T01

Re-runs options_backtest.py with the populated historical data
(30 trading days in options_chain_snapshots).

Stores ONE ROW PER (candidate, entry_date) — NOT aggregated per candidate.
This gives the OOS validator 1,500+ rows across dates instead of 65.

Reads from:  options_chain_snapshots (trade_date, 30 dates)
              option_structure_candidates
Writes to:   options_backtest_results (per-date rows)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
sys.path.insert(0, str(ROOT))

from src.dashboard.data import _db_path

LOT_SIZE = 100
SLIPPAGE_PCT = 0.5  # 0.5% slippage per side

OOS_APPROVED  = "OPTIONS_OOS_APPROVED_FOR_STUDY"
OOS_MONITOR   = "OPTIONS_OOS_MONITOR_ONLY"
OOS_BLOCKED   = "OPTIONS_OOS_BLOCKED"
INSUFFICIENT  = "INSUFFICIENT_HISTORY"
ILLIQUID      = "ILLIQUID_HISTORY"


def _db() -> Path:
    return _db_path()


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def get_historical_dates(n: int = 30) -> list[str]:
    """Return the last n trading dates present in chain snapshots (ASC order)."""
    conn = sqlite3.connect(str(_db()))
    c = conn.execute("""
        SELECT DISTINCT trade_date
        FROM options_chain_snapshots
        ORDER BY trade_date ASC
        LIMIT ?
    """, (n,))
    dates = [r[0] for r in c.fetchall()]
    conn.close()
    return dates


def load_candidates(min_liq: float = 20.0) -> list[dict]:
    """Load option structure candidates (non-blocked)."""
    conn = sqlite3.connect(str(_db()))
    c = conn.execute("""
        SELECT id, underlying, structure_type, maturity_date,
               net_debit, net_credit, max_profit, max_loss,
               breakeven, payoff_ratio, liquidity_score, risk_score,
               candidate_status, governance_status, legs_json, metadata_json
        FROM option_structure_candidates
        WHERE candidate_status NOT LIKE 'BLOQUEADO%'
        ORDER BY liquidity_score DESC, risk_score ASC
    """)
    rows = c.fetchall()
    conn.close()

    candidates = []
    for r in rows:
        if float(r[10] or 0) < min_liq:
            continue
        try:
            legs = json.loads(r[14]) if r[14] else []
        except Exception:
            legs = []
        candidates.append({
            "id":              r[0],
            "underlying":      r[1],
            "structure_type":  r[2],
            "maturity_date":   r[3],
            "net_debit":       r[4] or 0.0,
            "net_credit":     r[5] or 0.0,
            "max_profit":     r[6] or 0.0,
            "max_loss":       r[7] or 0.0,
            "breakeven":      r[8],
            "payoff_ratio":   r[9] or 0.0,
            "liquidity_score": r[10] or 0.0,
            "risk_score":     r[11] or 0.0,
            "status":         r[12],
            "governance":     r[13],
            "legs":           legs,
        })
    return candidates


def simulate_for_date(
    conn: sqlite3.Connection,
    candidate: dict,
    chain_date: str,
    trade_dates: list[str],
) -> dict | None:
    """
    Simulate ONE candidate entry on `chain_date`, exit on next available date.

    Returns None if no matching options found.
    """
    conn.row_factory = sqlite3.Row

    underlying    = candidate["underlying"]
    legs          = candidate["legs"]
    if not legs:
        return None

    option_types  = list(set(l["option_type"] for l in legs))
    placeholders  = ','.join('?' * len(option_types))

    # ── Entry ──────────────────────────────────────────────────────────────
    entry_rows = conn.execute(f"""
        SELECT option_ticker, option_type, strike, last_price, bid, ask,
               spread_pct, implied_volatility, liquidity_score,
               delta, theta, vega, gamma
        FROM options_chain_snapshots
        WHERE underlying=? AND trade_date=? AND option_type IN ({placeholders})
        ORDER BY strike
    """, [underlying, chain_date] + option_types).fetchall()

    if not entry_rows:
        return None

    chain_df = {str(r["option_ticker"]): r for r in entry_rows}

    entry_prices  = {}
    entry_spreads = []
    ivs_entry     = []
    liqs_entry    = []

    for leg in legs:
        ticker   = leg["option_ticker"]
        opt_type = leg["option_type"]
        strike   = float(leg["strike"])

        match = chain_df.get(ticker)
        if not match:
            type_matches = [r for r in entry_rows if str(r["option_type"]) == opt_type]
            if not type_matches:
                return None
            sorted_matches = sorted(type_matches, key=lambda r: abs(float(r["strike"]) - strike))
            if not sorted_matches:
                return None
            # Tolerance: 0.10 strike difference before calling it a mismatch
            if abs(float(sorted_matches[0]["strike"]) - strike) > 0.10:
                return None
            match = sorted_matches[0]

        price = float(match["bid"]) if float(match["bid"]) > 0 else float(match["last_price"])
        entry_prices[leg["direction"]] = entry_prices.get(leg["direction"], 0.0) + price

        sp = leg.get("spread_pct") or (match["spread_pct"] if match["spread_pct"] is not None else None)
        if sp is not None and float(sp) > 0:
            entry_spreads.append(float(sp))

        iv = match["implied_volatility"]
        if iv is not None and float(iv) > 0:
            ivs_entry.append(float(iv))

        ls = match["liquidity_score"]
        if ls is not None:
            liqs_entry.append(float(ls))

    # ── Exit ───────────────────────────────────────────────────────────────
    idx = trade_dates.index(chain_date)
    exit_date  = None
    exit_prices = {}
    exit_spreads = []
    ivs_exit    = []

    for next_idx in range(idx + 1, len(trade_dates)):
        next_date = trade_dates[next_idx]
        exit_rows = conn.execute(f"""
            SELECT option_ticker, option_type, strike, bid, ask, last_price, spread_pct,
                   implied_volatility
            FROM options_chain_snapshots
            WHERE underlying=? AND trade_date=? AND option_type IN ({placeholders})
        """, [underlying, next_date] + option_types).fetchall()

        if not exit_rows:
            continue

        exit_df = {str(r["option_ticker"]): r for r in exit_rows}
        all_found = True

        for leg in legs:
            ticker   = leg["option_ticker"]
            opt_type = leg["option_type"]
            strike   = float(leg["strike"])

            match = exit_df.get(ticker)
            if not match:
                type_matches = [r for r in exit_rows if str(r["option_type"]) == opt_type]
                if not type_matches:
                    all_found = False
                    break
                sorted_matches = sorted(type_matches, key=lambda r: abs(float(r["strike"]) - strike))
                if not sorted_matches:
                    all_found = False
                    break
                if abs(float(sorted_matches[0]["strike"]) - strike) > 0.10:
                    all_found = False
                    break
                match = sorted_matches[0]

            price = float(match["bid"]) if float(match["bid"]) > 0 else float(match["last_price"])
            exit_prices[leg["direction"]] = exit_prices.get(leg["direction"], 0.0) + price

            sp = match["spread_pct"]
            if sp is not None and float(sp) > 0:
                exit_spreads.append(float(sp))

            iv = match["implied_volatility"]
            if iv is not None and float(iv) > 0:
                ivs_exit.append(float(iv))

        if all_found:
            exit_date = next_date
            break

    # ── P&L calculation ──────────────────────────────────────────────────────
    # Directional signs:
    #   COMPRA = long leg  → you pay at entry, receive at exit
    #   VENDA  = short leg → you receive at entry, pay at exit
    #
    # For a put spread (bull put: sell high strike, buy low strike):
    #   net_debit  = compra_entry  - venda_entry   (> 0 = you pay)
    #   net_credit = compra_exit   - venda_exit    (> 0 = you receive)
    #   P&L        = net_credit - net_debit
    #
    compras_entry = entry_prices.get("COMPRA", 0.0)
    vendas_entry  = entry_prices.get("VENDA", 0.0)
    compras_exit  = exit_prices.get("COMPRA", 0.0) if exit_prices else 0.0
    vendas_exit   = exit_prices.get("VENDA", 0.0)  if exit_prices else 0.0

    # Directional cost: COMPRA is debit (you pay), VENDA is credit (you receive)
    net_debit  = max(compras_entry - vendas_entry, 0.0)  # always >= 0
    net_credit = max(compras_exit  - vendas_exit,  0.0)   # always >= 0

    pnl_reais = (net_credit - net_debit) * LOT_SIZE

    slippage = net_debit * (SLIPPAGE_PCT / 100) * 2
    pnl_after_slip = pnl_reais - slippage

    win = 1 if pnl_after_slip > 0 else 0
    pnl_pct = (pnl_after_slip / (net_debit * LOT_SIZE) * 100) if net_debit > 0 else 0.0

    holding_days = 0
    if exit_date:
        d1 = date.fromisoformat(chain_date)
        d2 = date.fromisoformat(exit_date)
        holding_days = max((d2 - d1).days, 0)

    # DTE at entry
    mat_str = candidate.get("maturity_date", "")
    dte_entry = 0
    if mat_str:
        try:
            mat_date = date.fromisoformat(mat_str)
            dte_entry = max((mat_date - date.fromisoformat(chain_date)).days, 0)
        except Exception:
            pass

    dte_exit = 0
    if exit_date and mat_str:
        try:
            mat_date = date.fromisoformat(mat_str)
            dte_exit = max((mat_date - date.fromisoformat(exit_date)).days, 0)
        except Exception:
            pass

    max_loss_lot  = abs(candidate["max_loss"] or 0) * LOT_SIZE
    max_profit_lot = (candidate["max_profit"] or 0.0) * LOT_SIZE

    return {
        "entry_date":  chain_date,
        "exit_date":   exit_date,
        "entry_price": round(compras_entry + vendas_entry, 4),
        "exit_price":  round(compras_exit + vendas_exit, 4),
        "pnl_reais":   round(pnl_reais, 2),
        "pnl_pct":     round(pnl_pct, 2),
        "win":         win,
        "holding_days": holding_days,
        "dte_entry":   dte_entry,
        "dte_exit":    dte_exit,
        "spread_entry": round(sum(entry_spreads) / len(entry_spreads), 2) if entry_spreads else 0.0,
        "spread_exit":  round(sum(exit_spreads)  / len(exit_spreads),  2) if exit_spreads  else 0.0,
        "slippage":     round(slippage, 2),
        "max_loss":     round(max_loss_lot, 2),
        "max_profit":   round(max_profit_lot, 2),
        "underlying_price_entry": 0.0,
        "liquidity_score": round(sum(liqs_entry) / len(liqs_entry), 1) if liqs_entry else 0.0,
        "iv_entry":     round(sum(ivs_entry) / len(ivs_entry), 4) if ivs_entry else 0.0,
        "iv_exit":      round(sum(ivs_exit)  / len(ivs_exit),  4) if ivs_exit  else 0.0,
        "regime":       "NEUTRAL_IV",
        "blocked_reason": None,
        "exit_found":   exit_date is not None,
    }


def compute_realized_metrics(cand_results: list[dict]) -> dict:
    """
    Compute realized performance metrics from historical simulation results.

    These metrics are based on actual P&L distribution from the simulation,
    NOT on theoretical max_profit/max_loss from the option structure.
    """
    pnls = [r["pnl_reais"] for r in cand_results if r.get("pnl_reais") is not None]
    if not pnls:
        return {
            "realized_avg_win": 0.0,
            "realized_avg_loss": 0.0,
            "realized_payoff": 0.0,
            "realized_win_rate": 0.0,
            "realized_sample_size": len(cand_results),
        }

    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total  = len(pnls)

    avg_win  = sum(wins)   / len(wins)   if wins   else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0  # negative

    # Payoff: avg_win / |avg_loss|
    if losses and avg_loss != 0.0:
        payoff = avg_win / abs(avg_loss)
    elif wins:
        # Conservative fallback: no losses observed in history
        # Use 50% of avg_win as loss proxy
        conservative_loss = avg_win * 0.5
        payoff = avg_win / conservative_loss if conservative_loss > 0 else 0.0
    else:
        payoff = 0.0  # all losses, no realized gains

    win_rate = len(wins) / total if total > 0 else 0.0

    return {
        "realized_avg_win":  round(avg_win, 2),
        "realized_avg_loss": round(avg_loss, 2),
        "realized_payoff":   round(payoff, 4),
        "realized_win_rate": round(win_rate, 4),
        "realized_sample_size": total,
    }


def classify_oos(
    results: list[dict],
    available_days: int,
) -> tuple[str, dict]:
    """Classify candidate based on historical simulation results.

    Returns: (oos_status, realized_metrics_dict)
    """
    if not results:
        return INSUFFICIENT, {}

    realized = compute_realized_metrics(results)
    wins = sum(1 for r in results if r.get("win", 0) == 1)
    total = len(results)
    win_rate = wins / total if total > 0 else 0.0

    pnls = [r.get("pnl_pct", 0.0) for r in results if r.get("pnl_pct") is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

    liqs = [r["liquidity_score"] for r in results if r.get("liquidity_score")]
    avg_liq = sum(liqs) / len(liqs) if liqs else 0.0

    payoff = realized["realized_payoff"]  # realized, not theoretical

    max_loss_val  = results[0].get("max_loss", 0.0) or 0.0  # theoretical structural loss
    max_profit_val = results[0].get("max_profit", 0.0) or 0.0  # theoretical structural profit

    if available_days < 5:
        return INSUFFICIENT, realized
    if avg_liq < 30:
        return ILLIQUID, realized
    if max_profit_val == float("inf") or max_loss_val <= 0:
        return OOS_BLOCKED, realized

    # Drawdown check using realized avg_pnl vs theoretical max_loss
    if avg_pnl < -max_loss_val * 0.3:
        return OOS_BLOCKED, realized

    if available_days >= 30 and avg_liq >= 50 and payoff >= 1.0:
        return OOS_APPROVED, realized
    elif available_days >= 15 and avg_liq >= 30 and (payoff >= 0.5 or win_rate >= 0.40):
        return OOS_MONITOR, realized
    elif available_days >= 10:
        return OOS_MONITOR, realized
    else:
        return OOS_BLOCKED, realized


def run_backtest(run_id: str, trade_dates: list[str]) -> dict:
    """
    Main backtest loop — stores ONE ROW PER (candidate, entry_date).

    Returns summary dict with per-candidate diagnostics.
    """
    candidates = load_candidates(min_liq=20.0)
    print(f"Candidates loaded: {len(candidates)}")

    conn = sqlite3.connect(str(_db()))
    conn.execute("PRAGMA busy_timeout = 10000")
    c = conn.cursor()
    now = _now()

    # Clear old run results
    c.execute("DELETE FROM options_backtest_results WHERE run_id = ?", (run_id,))
    conn.commit()

    # Per-candidate diagnostics accumulator
    diagnostics: dict[int, dict] = {}

    # Status counters
    status_counts = {
        OOS_APPROVED: 0, OOS_MONITOR: 0, OOS_BLOCKED: 0,
        INSUFFICIENT: 0, ILLIQUID: 0,
    }

    # Row INSERT template (34 columns)
    INSERT_SQL = """
        INSERT INTO options_backtest_results (
            run_id, run_date, candidate_id, structure_type, underlying,
            entry_date, exit_date, entry_price, exit_price,
            pnl_reais, pnl_pct, win, holding_days, dte_entry, dte_exit,
            spread_entry, spread_exit, slippage, max_loss, max_profit,
            underlying_price_entry, liquidity_score, iv_entry, iv_exit,
            regime, blocked_reason, oos_status, notes, created_at,
            realized_avg_win, realized_avg_loss, realized_payoff,
            realized_win_rate, realized_sample_size
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    total_rows_written = 0

    for candidate in candidates:
        cand_id    = candidate["id"]
        underlying = candidate["underlying"]
        stype      = candidate["structure_type"]

        # Per-candidate diagnostics
        diag = {
            "dates_evaluated": 0,
            "dates_chain_found": 0,
            "dates_simulated": 0,
            "dates_discarded": 0,
            "discard_reasons": [],
        }

        cand_results: list[dict] = []

        for td in trade_dates:
            diag["dates_evaluated"] += 1

            result = simulate_for_date(conn, candidate, td, trade_dates)

            if result is None:
                diag["dates_discarded"] += 1
                diag["discard_reasons"].append(f"{td}:no_chain_match")
                continue

            diag["dates_chain_found"] += 1
            if result["exit_found"]:
                diag["dates_simulated"] += 1
                cand_results.append(result)

        diagnostics[cand_id] = diag

        if not cand_results:
            # No simulation data for this candidate
            oos_status, realized = classify_oos([], diag["dates_evaluated"])
            c.execute(INSERT_SQL, (
                run_id, now[:10], cand_id, stype, underlying,
                None, None, None, None, None, None, 0, 0, None, None,
                None, None, None,
                abs(candidate["max_loss"] or 0) * LOT_SIZE,
                (candidate["max_profit"] or 0.0) * LOT_SIZE,
                None, None, None, None,
                None, "no_simulation_data", oos_status,
                f"Evaluated {diag['dates_evaluated']} dates; {diag['dates_chain_found']} chain found; "
                f"{diag['dates_simulated']} simulated; {diag['dates_discarded']} discarded — "
                f"reasons: {diag['discard_reasons'][:5]}",
                now,
                realized.get("realized_avg_win", 0.0),
                realized.get("realized_avg_loss", 0.0),
                realized.get("realized_payoff", 0.0),
                realized.get("realized_win_rate", 0.0),
                realized.get("realized_sample_size", 0),
            ))
            status_counts[oos_status] += 1
            continue

        # ── Persist ONE ROW PER (candidate, entry_date) ───────────────────
        for result in cand_results:
            c.execute(INSERT_SQL, (
                run_id, now[:10], cand_id, stype, underlying,
                result["entry_date"], result["exit_date"],
                result["entry_price"], result["exit_price"],
                result["pnl_reais"], result["pnl_pct"],
                result["win"], result["holding_days"],
                result["dte_entry"], result["dte_exit"],
                result["spread_entry"], result["spread_exit"],
                result["slippage"],
                result["max_loss"], result["max_profit"],
                result["underlying_price_entry"],
                result["liquidity_score"],
                result["iv_entry"], result["iv_exit"],
                result["regime"], result["blocked_reason"],
                None,  # oos_status set below per candidate
                None,  # notes set below
                now,
                None, None, None, None, None,  # realized metrics set via UPDATE below
            ))
            total_rows_written += 1

        # ── OOS classification for this candidate (from aggregated results) ─
        oos_status, realized = classify_oos(cand_results, diag["dates_evaluated"])
        status_counts[oos_status] += 1

        # Update oos_status on all rows for this candidate in this run
        c.execute("""
            UPDATE options_backtest_results
            SET oos_status=?, notes=?,
               realized_avg_win=?, realized_avg_loss=?,
               realized_payoff=?, realized_win_rate=?, realized_sample_size=?
            WHERE run_id=? AND candidate_id=? AND oos_status IS NULL
        """, (
            oos_status,
            f"Aggregated {len(cand_results)} entries; "
            f"chain_found={diag['dates_chain_found']}; "
            f"simulated={diag['dates_simulated']}; "
            f"discarded={diag['dates_discarded']}; "
            f"payoff_realized={realized.get('realized_payoff', 0.0):.4f}",
            realized.get("realized_avg_win", 0.0),
            realized.get("realized_avg_loss", 0.0),
            realized.get("realized_payoff", 0.0),
            realized.get("realized_win_rate", 0.0),
            realized.get("realized_sample_size", len(cand_results)),
            run_id, cand_id,
        ))

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "run_id": run_id,
        "run_date": now[:10],
        "trading_days": len(trade_dates),
        "date_range": f"{trade_dates[0]} to {trade_dates[-1]}",
        "total_candidates": len(candidates),
        "total_rows_written": total_rows_written,
        "oos_summary": status_counts,
        "diagnostics": diagnostics,
    }


def main():
    run_id = f"BT_HIST_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    trade_dates = get_historical_dates(30)

    print("=" * 70)
    print("  Options Historical Backtest Runner — M010.5 S02 T01")
    print(f"  Run: {run_id}")
    print(f"  Dates: {len(trade_dates)} ({trade_dates[0]} to {trade_dates[-1]})")
    print("=" * 70)

    result = run_backtest(run_id, trade_dates)

    print(f"\n{'='*70}")
    print("  Backtest Results")
    print(f"{'='*70}")
    print(f"  Run ID:         {result['run_id']}")
    print(f"  Date range:     {result['date_range']}")
    print(f"  Trading days:   {result['trading_days']}")
    print(f"  Candidates:     {result['total_candidates']}")
    print(f"  Rows written:   {result['total_rows_written']}")
    print(f"\n  OOS Summary:")
    for status, count in result["oos_summary"].items():
        print(f"    {status}: {count}")

    print(f"\n  Per-candidate diagnostics (top 10 by simulated dates):")
    sorted_diag = sorted(
        result["diagnostics"].items(),
        key=lambda x: x[1]["dates_simulated"],
        reverse=True,
    )
    for cand_id, diag in sorted_diag[:10]:
        print(f"    cand {cand_id}: eval={diag['dates_evaluated']} "
              f"chain={diag['dates_chain_found']} sim={diag['dates_simulated']} "
              f"disc={diag['dates_discarded']}")

    print(f"\n[OK] Backtest complete: {result['run_id']}")
    print(f"     Expected ~{30 * result['total_candidates']} rows, got {result['total_rows_written']}")

    # Write diagnostics JSON for reference
    diag_path = ROOT / "data" / f"backtest_diagnostics_{run_id}.json"
    with open(diag_path, "w") as f:
        json.dump(result["diagnostics"], f, indent=2)
    print(f"     Diagnostics: {diag_path}")


if __name__ == "__main__":
    main()