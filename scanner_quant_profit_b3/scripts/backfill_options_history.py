#!/usr/bin/env python3
"""
Options Historical Backfill — M010.5 S01 T02

Repopulates options_chain_snapshots and options_greeks_snapshot
for the last N trading days using cotahist_daily (market_type 070/080).

Idempotent: skips dates already processed (checks options_chain_snapshots).

Usage:
  python scripts/backfill_options_history.py [--days N] [--dates YYYY-MM-DD,YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Bootstrap
_FILE = Path(__file__).resolve()
ROOT = _FILE.parents[1]
sys.path.insert(0, str(ROOT))

from src.options.greeks import (
    black_scholes_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    estimate_implied_volatility,
)

DB_PATH = ROOT / "data" / "database" / "scanner_quant.db"

# Priority underlyings (first 4 chars of ticker)
PRIORITY = ["PETR", "VALE", "ITUB", "BBAS", "BBDC", "WEGE", "SUZB"]
RISK_FREE = 0.1475  # SELIC proxy — fixed for all dates
MAX_SPREAD_BLOCK = 40.0  # % — spread above this blocks the option
BATCH_SIZE = 1000  # rows per INSERT batch


def get_trading_dates(n: int = 30) -> list[str]:
    """Get the last N trading dates that have options in cotahist_daily."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        SELECT trade_date
        FROM cotahist_daily
        WHERE market_type IN ('070', '080')
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT ?
    """, (n,))
    dates = [r[0] for r in c.fetchall()]
    conn.close()
    return dates


def get_underlying_prices(conn: sqlite3.Connection, trade_date: str) -> dict[str, float]:
    """Load stock prices (market_type 010) for priority underlyings."""
    placeholders = ','.join('?' * len(PRIORITY))
    c = conn.execute(f"""
        SELECT SUBSTR(ticker,1,4), close
        FROM cotahist_daily
        WHERE market_type = '010'
          AND trade_date = ?
          AND SUBSTR(ticker,1,4) IN ({placeholders})
    """, (trade_date, *PRIORITY))
    result = {}
    for row in c.fetchall():
        result[str(row[0])] = float(row[1]) if row[1] and row[1] > 0 else 0.0
    return result


def get_already_processed_dates() -> set[str]:
    """Returns set of trade_dates already in options_chain_snapshots."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.execute("SELECT DISTINCT trade_date FROM options_chain_snapshots")
    dates = {r[0] for r in c.fetchall()}
    conn.close()
    return dates


def classify_moneyness(S: float, K: float, opt_type: str) -> tuple[str, float]:
    if opt_type == "CALL":
        if K < S: return ("ITM", (S - K) / S * 100)
        elif K > S: return ("OTM", (K - S) / S * 100)
        else: return ("ATM", 0.0)
    else:
        if K > S: return ("ITM", (K - S) / S * 100)
        elif K < S: return ("OTM", (S - K) / S / S * 100)
        else: return ("ATM", 0.0)


def calc_liquidity_score(volume: float, trades: int) -> float:
    if volume <= 0 or trades <= 0:
        return 0.0
    vol_score = min(math.log1p(volume) / math.log1p(10_000_000), 1.0) * 50
    trade_score = min(trades / 100, 1.0) * 50
    return round(vol_score + trade_score, 1)


def backfill_date(trade_date: str, dry_run: bool = False) -> dict:
    """Populate options_chain_snapshots for a single trade_date."""
    captured_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Load underlying prices
    underlying_prices = get_underlying_prices(conn, trade_date)
    if not underlying_prices:
        conn.close()
        return {"date": trade_date, "status": "no_underlying_prices", "options": 0}

    # Load options for all priority underlyings
    all_rows = []
    for prefix in PRIORITY:
        S = underlying_prices.get(prefix, 0.0)
        if S <= 0:
            continue

        rows = c.execute("""
            SELECT
                ticker, strike, option_type, expiration_date,
                close, best_bid, best_ask,
                quantity, trades, volume
            FROM cotahist_daily
            WHERE market_type IN ('070', '080')
              AND SUBSTR(ticker, 1, 4) = ?
              AND trade_date = ?
              AND strike > 0
            ORDER BY quantity DESC
        """, (prefix, trade_date)).fetchall()

        for row in rows:
            ticker, strike, option_type, expiry, close, bid, ask, qty, trades_cnt, vol = row

            # Skip zero/negative prices
            if not close or close <= 0:
                continue

            # Spread filter
            spread_pct = 0.0
            if bid and ask and bid > 0 and ask > bid:
                spread_pct = ((ask - bid) / bid) * 100
                if spread_pct > MAX_SPREAD_BLOCK:
                    continue

            # DTE
            ref = date.fromisoformat(trade_date)
            try:
                exp_date = date.fromisoformat(str(expiry))
                dte = max((exp_date - ref).days, 1)
            except (ValueError, TypeError):
                dte = 30  # fallback

            moneyness_cls, moneyness_pct = classify_moneyness(S, float(strike), str(option_type))

            # Greeks
            K = float(strike)
            price = float(close)
            opt = str(option_type)
            T = max(dte / 365.0, 1e-4)

            iv = estimate_implied_volatility(price, S, K, T, RISK_FREE, opt)
            iv_ok = not (iv != iv) and iv > 0 and iv < 5.0
            sigma = iv if iv_ok else 0.30  # fallback to 30% HV

            # Intrinsic / time value
            if opt == "CALL":
                intrinsic = max(0.0, S - K)
            else:
                intrinsic = max(0.0, K - S)
            time_val = max(0.0, price - intrinsic)

            # Breakeven
            if opt == "CALL":
                breakeven = K + time_val
            else:
                breakeven = K - time_val

            bs = black_scholes_price(S, K, T, RISK_FREE, sigma, opt)
            delta = calculate_delta(S, K, T, RISK_FREE, sigma, opt)
            gamma = calculate_gamma(S, K, T, RISK_FREE, sigma)
            theta = calculate_theta(S, K, T, RISK_FREE, sigma, opt)
            vega = calculate_vega(S, K, T, RISK_FREE, sigma)
            risk_score = round(min(abs(K - S) / S * 100, 50) / 50 * 100, 1)

            all_rows.append({
                "captured_at": captured_at,
                "trade_date": trade_date,
                "option_ticker": str(ticker),
                "underlying": prefix,
                "option_type": opt,
                "strike": K,
                "maturity_date": str(expiry),
                "days_to_maturity": dte,
                "last_price": price,
                "bid": float(bid) if bid else 0.0,
                "ask": float(ask) if ask else 0.0,
                "spread_pct": round(spread_pct, 4),
                "volume": float(vol) if vol else 0.0,
                "trades": int(trades_cnt) if trades_cnt else 0,
                "financial_volume": float(qty or 0) * price,
                "open_interest": None,
                "underlying_price": S,
                "moneyness_pct": round(moneyness_pct, 4),
                "moneyness_class": moneyness_cls,
                "intrinsic_value": round(intrinsic, 4),
                "extrinsic_value": round(time_val, 4),
                "breakeven": round(breakeven, 4),
                "implied_volatility": round(iv, 6) if iv_ok else float("nan"),
                "historical_volatility": 0.30,
                "delta": round(delta, 6),
                "gamma": round(gamma, 6),
                "theta": round(theta, 6),
                "vega": round(vega, 6),
                "liquidity_score": calc_liquidity_score(float(vol or 0), int(trades_cnt or 0)),
                "risk_score": risk_score,
                "metadata_json": '{"source":"cotahist_daily","backfill":"M0105"}',
            })

    conn.close()

    if not all_rows:
        return {"date": trade_date, "status": "no_options", "options": 0}

    if dry_run:
        return {"date": trade_date, "status": "dry_run", "options": len(all_rows)}

    # Insert in batches
    conn = sqlite3.connect(str(DB_PATH))
    cols = [
        "captured_at", "trade_date", "option_ticker", "underlying", "option_type",
        "strike", "maturity_date", "days_to_maturity",
        "last_price", "bid", "ask", "spread_pct",
        "volume", "trades", "financial_volume", "open_interest",
        "underlying_price",
        "moneyness_pct", "moneyness_class",
        "intrinsic_value", "extrinsic_value", "breakeven",
        "implied_volatility", "historical_volatility",
        "delta", "gamma", "theta", "vega",
        "liquidity_score", "risk_score",
        "metadata_json",
    ]

    for i in range(0, len(all_rows), BATCH_SIZE):
        batch = all_rows[i:i+BATCH_SIZE]
        # Replace inf/-inf with None
        for row in batch:
            for col in cols:
                val = row.get(col)
                if isinstance(val, float) and (val != val or abs(val) == float('inf')):
                    row[col] = None

        conn.executemany(
            f"""INSERT OR REPLACE INTO options_chain_snapshots
                ({','.join(cols)})
                VALUES ({','.join(':'+c for c in cols)})""",
            batch
        )
        conn.commit()

    conn.close()
    return {"date": trade_date, "status": "inserted", "options": len(all_rows)}


def backfill_greeks(trade_date: str) -> dict:
    """Calculate and populate options_greeks_snapshot from options_chain_snapshots for a date."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""
        SELECT id, option_ticker, underlying, option_type, strike,
               maturity_date, days_to_maturity, last_price, bid, ask,
               volume, trades, liquidity_score, moneyness_class, moneyness_pct,
               implied_volatility, underlying_price
        FROM options_chain_snapshots
        WHERE trade_date = ?
          AND implied_volatility IS NOT NULL
          AND implied_volatility > 0
          AND implied_volatility < 5
    """, (trade_date,))

    rows = c.fetchall()
    if not rows:
        conn.close()
        return {"date": trade_date, "status": "no_data", "greeks": 0}

    greeks_rows = []
    captured_at = datetime.now(timezone(timedelta(hours=-3))).isoformat()

    for row in rows:
        (snap_id, ticker, underlying, opt_type, strike,
         mat, dte, price, bid, ask, vol, trades_cnt, liq,
         moneyness_cls, moneyness_pct, iv, S) = row

        K = float(strike) if strike else 0
        S_val = float(S) if S else 0
        price_val = float(price) if price else 0
        dte_val = int(dte) if dte else 0
        T = max(dte_val / 365.0, 1e-4)
        iv_val = float(iv) if iv else 0.0
        opt = str(opt_type)
        risk_free = RISK_FREE

        try:
            rho_val = 0.0  # simplified
            vanna = 0.0
            charm = 0.0
            vomma = 0.0
            speed = 0.0
            intrinsic = max(0, S_val - K) if opt == "CALL" else max(0, K - S_val)
            time_val = max(0, price_val - intrinsic)

            greeks_rows.append({
                "captured_at": captured_at,
                "trade_date": trade_date,
                "underlying": str(underlying),
                "ticker": str(ticker),
                "option_type": opt,
                "strike": K,
                "expiry": str(mat) if mat else None,
                "dte": dte_val,
                "price": price_val,
                "volume": float(vol) if vol else 0.0,
                "trades": int(trades_cnt) if trades_cnt else 0,
                "liq_score": float(liq) if liq else 0.0,
                "moneyness": str(moneyness_cls) if moneyness_cls else "UNKNOWN",
                "moneyness_pct": float(moneyness_pct) if moneyness_pct else 0.0,
                "iv_implied": round(iv_val, 6),
                "iv_hv": 0.30,
                "iv_vs_hv": round(iv_val - 0.30, 6) if iv_val else 0.0,
                "delta": round(calculate_delta(S_val, K, T, risk_free, iv_val, opt), 6),
                "rho": rho_val,
                "gamma": round(calculate_gamma(S_val, K, T, risk_free, iv_val), 6),
                "theta": round(calculate_theta(S_val, K, T, risk_free, iv_val, opt), 6),
                "vega": round(calculate_vega(S_val, K, T, risk_free, iv_val), 6),
                "vanna": vanna,
                "charm": charm,
                "vomma": vomma,
                "speed": speed,
                "intrinsic_value": round(intrinsic, 4),
                "time_value": round(time_val, 4),
                "stock_price": S_val,
            })
        except Exception:
            continue

    if not greeks_rows:
        conn.close()
        return {"date": trade_date, "status": "calc_error", "greeks": 0}

    # Insert
    g_cols = [
        "captured_at", "trade_date", "underlying", "ticker", "option_type",
        "strike", "expiry", "dte", "price", "volume", "trades",
        "liq_score", "moneyness", "moneyness_pct",
        "iv_implied", "iv_hv", "iv_vs_hv",
        "delta", "rho", "gamma", "theta", "vega",
        "vanna", "charm", "vomma", "speed",
        "intrinsic_value", "time_value", "stock_price",
    ]

    for batch in [greeks_rows[i:i+BATCH_SIZE] for i in range(0, len(greeks_rows), BATCH_SIZE)]:
        conn.executemany(
            f"""INSERT OR REPLACE INTO options_greeks_snapshot
                ({','.join(g_cols)})
                VALUES ({','.join(':'+c for c in g_cols)})""",
            batch
        )
        conn.commit()

    conn.close()
    return {"date": trade_date, "status": "inserted", "greeks": len(greeks_rows)}


def main():
    parser = argparse.ArgumentParser(description="Options Historical Backfill")
    parser.add_argument("--days", type=int, default=30, help="Number of trading days to backfill (default: 30)")
    parser.add_argument("--dates", type=str, default=None, help="Comma-separated dates (overrides --days)")
    parser.add_argument("--dry-run", action="store_true", help="Count options without inserting")
    parser.add_argument("--chain-only", action="store_true", help="Skip greeks calculation")
    args = parser.parse_args()

    print("=" * 70)
    print("  Options Historical Backfill — M010.5 S01 T02")
    print("=" * 70)

    if args.dates:
        trade_dates = [d.strip() for d in args.dates.split(",")]
    else:
        trade_dates = get_trading_dates(args.days)

    already = get_already_processed_dates()
    to_process = [d for d in trade_dates if d not in already]

    print(f"Target: {len(trade_dates)} dates | Already done: {len(already)} | To process: {len(to_process)}")

    if not to_process:
        print("Nothing to do — all dates already processed.")
        return

    total_chain = 0
    total_greeks = 0
    errors = []

    for i, td in enumerate(to_process):
        print(f"\n[{i+1}/{len(to_process)}] {td}...", end=" ", flush=True)

        # Chain snapshot
        if not args.chain_only:
            result = backfill_date(td, dry_run=args.dry_run)
        else:
            result = {"date": td, "status": "skipped", "options": 0}

        if args.dry_run:
            print(f"DRY-RUN: {result['options']} options would be inserted")
            total_chain += result["options"]
            continue

        if result["status"] == "inserted":
            print(f"chain={result['options']}", end=" ", flush=True)
            total_chain += result["options"]

            # Greeks
            if not args.chain_only:
                g_result = backfill_greeks(td)
                if g_result["status"] == "inserted":
                    print(f"greeks={g_result['greeks']}", end="", flush=True)
                    total_greeks += g_result["greeks"]
                else:
                    print(f"greeks={g_result['status']}", end="", flush=True)
            print(" ✓")
        elif result["status"] == "no_options":
            print("no options")
        elif result["status"] == "no_underlying_prices":
            print("NO UNDERLYING PRICES — SKIPPED")
            errors.append((td, "no_underlying_prices"))
        else:
            print(f"ERROR: {result}")
            errors.append((td, result.get("status", "unknown")))

    print(f"\n{'='*70}")
    print(f"  Backfill complete")
    print(f"  Dates processed: {len(to_process)}")
    print(f"  Chain snapshots: {total_chain:,}")
    print(f"  Greeks rows: {total_greeks:,}")
    if errors:
        print(f"  Errors: {len(errors)}")
        for e in errors:
            print(f"    {e[0]}: {e[1]}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()