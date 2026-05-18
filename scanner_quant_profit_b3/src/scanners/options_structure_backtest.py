"""CLI de backtest preliminar de estruturas de opções."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.options.options_backtest_governance import evaluate_options_backtest_candidate
from src.options.options_backtest_store import save_option_structure_backtest_run
from src.options.options_backtest_summary import generate_options_backtest_report, summarize_by_structure_type, summarize_by_underlying, summarize_structure_backtest
from src.options.options_history import get_available_option_history_range, load_options_chain_snapshots
from src.options.structure_backtest import run_structure_backtest
from src.utils import load_config, project_path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _write_csv(results: pd.DataFrame, summary: dict[str, Any]) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "results": reports / f"option_structure_backtest_results_{stamp}.csv",
        "summary": reports / f"option_structure_backtest_summary_{stamp}.csv",
    }
    results.to_csv(paths["results"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(paths["summary"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    underlyings: list[str] | None = None,
    structure: str = "LONG_CALL",
    min_dte: int = 7,
    max_dte: int = 90,
    target_moneyness: str | None = None,
    min_liquidity_score: float = 0,
    max_spread_pct: float = 999,
    holding_days: int = 5,
    exit_at_expiry: bool = False,
    cost_bps: float = 10,
    slippage_bps: float = 5,
    save_db: bool = False,
    write_csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = _now()
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    coverage = get_available_option_history_range(db)
    chain = load_options_chain_snapshots(db, start, end, underlyings)
    rules = {
        "underlyings": underlyings,
        "min_dte": min_dte,
        "max_dte": max_dte,
        "target_moneyness": target_moneyness,
        "min_liquidity_score": min_liquidity_score,
        "max_spread_pct": max_spread_pct,
    }
    if chain.empty:
        results = pd.DataFrame()
        summary = summarize_structure_backtest(results)
        status = "INSUFFICIENT_DATA"
        print("Histórico de cadeia de opções insuficiente para backtest.")
    else:
        results = run_structure_backtest(chain, structure, rules, {"holding_days": holding_days, "exit_at_expiry": exit_at_expiry}, {"cost_bps": cost_bps, "slippage_bps": slippage_bps})
        summary = summarize_structure_backtest(results)
        status = "SUCCESS" if summary["total_trades"] > 0 else "INSUFFICIENT_DATA"
    finished = _now()
    summary.update(
        {
            "started_at": started,
            "finished_at": finished,
            "status": status,
            "start_date": start,
            "end_date": end,
            "underlyings": ",".join(underlyings or []),
            "structure_type": structure,
            "entries_count": summary.get("total_trades", 0),
            "metadata": {"coverage": coverage, "cost_bps": cost_bps, "slippage_bps": slippage_bps},
        }
    )
    governance = evaluate_options_backtest_candidate(summary)
    summary["governance_status"] = governance["governance_status"]
    paths = _write_csv(results, summary) if write_csv else {}
    run_id = None if dry_run or not save_db else save_option_structure_backtest_run(db, summary, results)

    print("\nOPTIONS STRUCTURE BACKTEST")
    print(f"Status: {status}")
    print(f"Estrutura: {structure}")
    print(f"Entradas: {summary['total_trades']}")
    print(f"Concluídas: {summary['completed_count']}")
    print(f"Win rate: {summary['win_rate']}%")
    print(f"Retorno líquido médio: {summary['mean_net_return']}%")
    print(f"Governança: {governance['governance_status']}")
    print(generate_options_backtest_report(summary))
    if run_id:
        print(f"Run salvo: option_structure_backtest_run_id={run_id}")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {
        "results": results,
        "summary": summary,
        "governance": governance,
        "by_structure": summarize_by_structure_type(results),
        "by_underlying": summarize_by_underlying(results),
        "run_id": run_id,
        "csv_paths": paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest preliminar de estruturas de opções.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--underlyings", nargs="*", default=None)
    parser.add_argument("--structure", default="LONG_CALL")
    parser.add_argument("--min-dte", type=int, default=7)
    parser.add_argument("--max-dte", type=int, default=90)
    parser.add_argument("--target-moneyness")
    parser.add_argument("--min-liquidity-score", type=float, default=0)
    parser.add_argument("--max-spread-pct", type=float, default=999)
    parser.add_argument("--holding-days", type=int, default=5)
    parser.add_argument("--exit-at-expiry", action="store_true")
    parser.add_argument("--cost-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        underlyings=args.underlyings,
        structure=args.structure,
        min_dte=args.min_dte,
        max_dte=args.max_dte,
        target_moneyness=args.target_moneyness,
        min_liquidity_score=args.min_liquidity_score,
        max_spread_pct=args.max_spread_pct,
        holding_days=args.holding_days,
        exit_at_expiry=args.exit_at_expiry,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        save_db=args.save_db,
        write_csv=args.write_csv,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
