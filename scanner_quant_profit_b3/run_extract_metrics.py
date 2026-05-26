#!/usr/bin/env python3
"""
run_extract_metrics.py
-----------------------
M017-S03 — Metric Extraction Engine runner.

Modes:
  --canary          EGIE3 dry-run (default)
  --needs-financials  18 NEEDS_FINANCIALS batch (dry-run unless --write)
  --all             All active tickers (requires --write to persist)
  --tickers A B C   Specific tickers

Flags:
  --write           Persist to valuation_financial_inputs (default: dry-run)
  --bank-only       Only process bank tickers
  --no-bank         Exclude bank tickers

Usage:
    cd 12_PYTHON
    ENV=development python run_extract_metrics.py --canary
    ENV=development python run_extract_metrics.py --canary --write
    ENV=development python run_extract_metrics.py --needs-financials
    ENV=development python run_extract_metrics.py --all --write
"""
from __future__ import annotations

import argparse
import json
import os
import sys

os.environ.setdefault("ENV", "development")

from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.ingestion.metric_extractor import extract_ticker, extract_all, BANK_TICKERS

CANARY_TICKER = "EGIE3"

NEEDS_FINANCIALS_18 = [
    "EQTL3", "AMOB3", "VAMO3", "AURE3", "RECV3", "INTR4",
    "BRAV3", "CMIN3", "AXIA3", "RAIZ4", "RDOR3", "HAPV3",
    "SMTO3", "CRFB3", "ALOS3", "IGTI11", "COGN3", "AZUL4",
]


def _fmt_val(v: float) -> str:
    """Format large BRL value for display."""
    if abs(v) >= 1e9:
        return f"R${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"R${v/1e6:,.2f}M"
    return f"R${v:,.0f}"


def print_canary_detail(result: dict) -> None:
    """Print detailed metric breakdown for canary ticker."""
    ticker = result["ticker"]
    print(f"\n{'='*65}")
    print(f"CANARY: {ticker} {'[BANK]' if result['is_bank'] else '[NON-BANK]'}")
    print(f"  Periods processed : {result['periods_processed']}")
    print(f"  Metrics extracted : {result['metrics_extracted']}")
    print(f"  Errors            : {len(result['errors'])}")

    if result["errors"]:
        print("\n  ERRORS:")
        for e in result["errors"]:
            print(f"    ❌ {e}")

    mc = result.get("metric_counts", {})
    if mc:
        print(f"\n  Metric coverage ({len(mc)} distinct metrics):")
        for metric, count in sorted(mc.items()):
            print(f"    {metric:<35} {count:>3} periods")

    print(f"{'='*65}")


def print_batch_summary(global_result: dict) -> None:
    """Print batch summary table."""
    summaries = global_result["ticker_summaries"]
    print(f"\n{'='*75}")
    print(f"BATCH SUMMARY — {global_result['total_tickers']} tickers")
    print(f"  Total records   : {global_result['total_records']:,}")
    print(f"  Total errors    : {global_result['total_errors']}")
    print(f"{'='*75}")
    print(f"{'Ticker':<10} {'Bank':<5} {'Periods':>8} {'Records':>8} {'Errors':>7} {'Metrics':>8}")
    print("-" * 55)
    for s in summaries:
        mc_count = len(s.get("metric_counts", {}))
        print(
            f"  {s['ticker']:<8} {'Y' if s['is_bank'] else 'N':<4} "
            f"{s['periods_processed']:>8} {s['metrics_upserted']:>8} "
            f"{len(s['errors']):>7} {mc_count:>8}"
        )

    missing = global_result.get("missing_metrics", {})
    if missing:
        print(f"\n  ⚠ Missing key metrics:")
        for m, tickers_list in sorted(missing.items()):
            print(f"    {m:<35}: {', '.join(tickers_list[:10])}"
                  + ("..." if len(tickers_list) > 10 else ""))
    print(f"{'='*75}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M017-S03 Metric Extraction Engine")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--canary",           action="store_true", help="Run canary (EGIE3) only")
    group.add_argument("--needs-financials", action="store_true", help="Run 18 NEEDS_FINANCIALS batch")
    group.add_argument("--all",              action="store_true", help="Run all active tickers")
    group.add_argument("--tickers",          nargs="+",           help="Run specific tickers")
    parser.add_argument("--write",           action="store_true", help="Persist to DB (default: dry-run)")
    parser.add_argument("--bank-only",       action="store_true", help="Only bank tickers")
    parser.add_argument("--no-bank",         action="store_true", help="Exclude bank tickers")
    args = parser.parse_args()

    # Default to canary
    if not any([args.canary, args.needs_financials, args.all, args.tickers]):
        args.canary = True

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"\nM017-S03 Metric Extraction Engine — {mode}")

    if args.canary:
        print(f"Mode: CANARY ({CANARY_TICKER})")
        result = extract_ticker(CANARY_TICKER, write=args.write)
        print_canary_detail(result)

    elif args.tickers:
        tickers_list = args.tickers
        if args.bank_only:
            tickers_list = [t for t in tickers_list if t.upper() in BANK_TICKERS]
        elif args.no_bank:
            tickers_list = [t for t in tickers_list if t.upper() not in BANK_TICKERS]
        print(f"Mode: SPECIFIC TICKERS — {tickers_list}")
        result = extract_all(tickers=tickers_list, write=args.write)
        print_batch_summary(result)

    elif args.needs_financials:
        tickers_list = NEEDS_FINANCIALS_18
        if args.bank_only:
            tickers_list = [t for t in tickers_list if t.upper() in BANK_TICKERS]
        elif args.no_bank:
            tickers_list = [t for t in tickers_list if t.upper() not in BANK_TICKERS]
        print(f"Mode: 18 NEEDS_FINANCIALS ({len(tickers_list)} tickers)")
        result = extract_all(tickers=tickers_list, write=args.write)
        print_batch_summary(result)

    elif args.all:
        print("Mode: ALL ACTIVE TICKERS")
        if args.bank_only:
            bank_tickers = list(BANK_TICKERS)
            result = extract_all(tickers=bank_tickers, write=args.write)
        elif args.no_bank:
            result = extract_all(write=args.write)
            # Filter out banks from result
        else:
            result = extract_all(write=args.write)
        print_batch_summary(result)


if __name__ == "__main__":
    main()
