"""CLI de walk-forward fora da amostra para estruturas de opções."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.options.options_context_analysis import (
    attach_event_context_to_options_results,
    attach_regime_context_to_options_results,
    summarize_options_by_event_context,
    summarize_options_by_regime,
)
from src.options.options_history import load_options_chain_snapshots
from src.options.options_oos_governance import evaluate_options_walk_forward_governance, generate_options_oos_governance_report
from src.options.options_stability import (
    detect_options_stability_issues,
    summarize_by_dte_bucket,
    summarize_by_liquidity_bucket,
    summarize_by_moneyness_bucket,
    summarize_by_structure_type,
)
from src.options.options_walk_forward import generate_options_walk_forward_report, run_options_walk_forward, summarize_options_walk_forward
from src.options.options_walk_forward_store import save_options_walk_forward_run
from src.options.structure_backtest import run_structure_backtest
from src.utils import load_config, project_path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_table(db_path: Path, table: str) -> pd.DataFrame:
    import sqlite3

    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table}", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _context_summary(context_results: pd.DataFrame, with_regimes: bool, with_events: bool) -> pd.DataFrame:
    frames = []
    if with_regimes:
        regime = summarize_options_by_regime(context_results)
        if not regime.empty:
            frames.append(regime.rename(columns={"primary_regime": "context_value"}).assign(context_type="primary_regime"))
    if with_events:
        event = summarize_options_by_event_context(context_results)
        if not event.empty:
            frames.append(event)
    if not frames:
        return pd.DataFrame(columns=["context_type", "context_value", "trades", "mean_net_return", "win_rate", "profit_factor", "avg_cost_drag", "skipped_pct", "metadata_json"])
    out = pd.concat(frames, ignore_index=True)
    out["metadata_json"] = "{}"
    return out


def _write_csv(results: pd.DataFrame, summary: dict[str, Any], context: pd.DataFrame) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "results": reports / f"option_walk_forward_results_{stamp}.csv",
        "summary": reports / f"option_walk_forward_summary_{stamp}.csv",
        "context": reports / f"option_context_summary_{stamp}.csv",
    }
    results.to_csv(paths["results"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(paths["summary"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    context.to_csv(paths["context"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    underlyings: list[str] | None = None,
    structure: str = "LONG_CALL",
    train_months: int = 3,
    test_months: int = 1,
    min_dte: int = 7,
    max_dte: int = 90,
    target_moneyness: str | None = None,
    min_liquidity_score: float = 0,
    max_spread_pct: float = 999,
    holding_days: int = 5,
    cost_bps: float = 10,
    slippage_bps: float = 5,
    with_regimes: bool = False,
    with_events: bool = False,
    save_db: bool = False,
    write_csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = _now()
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    chain = load_options_chain_snapshots(db, start, end, underlyings)
    rules = {
        "underlyings": underlyings,
        "min_dte": min_dte,
        "max_dte": max_dte,
        "target_moneyness": target_moneyness,
        "min_liquidity_score": min_liquidity_score,
        "max_spread_pct": max_spread_pct,
    }
    exit_rules = {"holding_days": holding_days}
    cost_model = {"cost_bps": cost_bps, "slippage_bps": slippage_bps}
    if chain.empty:
        wf_results = pd.DataFrame()
        summary = summarize_options_walk_forward(wf_results)
        status = "INSUFFICIENT_DATA"
    else:
        wf_results = run_options_walk_forward(chain, structure, rules, exit_rules, cost_model, train_months, test_months)
        summary = summarize_options_walk_forward(wf_results)
        status = "SUCCESS" if summary["windows_count"] else "INSUFFICIENT_DATA"

    full_results = run_structure_backtest(chain, structure, rules, exit_rules, cost_model) if not chain.empty else pd.DataFrame()
    context_results = full_results.copy()
    if with_regimes and not context_results.empty:
        context_results = attach_regime_context_to_options_results(context_results, _read_table(db, "market_regime_daily"))
    if with_events and not context_results.empty:
        context_results = attach_event_context_to_options_results(context_results, _read_table(db, "market_events"))
    context_summary = _context_summary(context_results, with_regimes, with_events)
    for label, frame in [
        ("dte_bucket", summarize_by_dte_bucket(full_results)),
        ("moneyness_bucket", summarize_by_moneyness_bucket(full_results)),
        ("structure_type", summarize_by_structure_type(full_results)),
        ("liquidity_bucket", summarize_by_liquidity_bucket(full_results)),
    ]:
        if not frame.empty:
            context_summary = pd.concat([context_summary, frame.rename(columns={label: "context_value"}).assign(context_type=label, metadata_json="{}")], ignore_index=True)
    stability_issues = detect_options_stability_issues(summarize_by_dte_bucket(full_results))

    governance = evaluate_options_walk_forward_governance(summary)
    finished = _now()
    summary.update(
        {
            "started_at": started,
            "finished_at": finished,
            "status": status,
            "start_date": start,
            "end_date": end,
            "structure_type": structure,
            "train_months": train_months,
            "test_months": test_months,
            "governance_status": governance["governance_status"],
            "metadata": {"underlyings": underlyings or [], "stability_issues": stability_issues, "cost_bps": cost_bps, "slippage_bps": slippage_bps},
        }
    )
    paths = _write_csv(wf_results, summary, context_summary) if write_csv else {}
    run_id = None if dry_run or not save_db else save_options_walk_forward_run(db, summary, wf_results, context_summary)

    print("\nOPTIONS WALK-FORWARD ANALYSIS")
    print(f"Status: {status}")
    print(f"Estrutura: {structure}")
    print(f"Janelas: {summary['windows_count']}")
    print(f"Janelas positivas: {summary['positive_windows_pct']}%")
    print(f"Retorno líquido médio teste: {summary['mean_test_net_return']}%")
    print(f"Robustez: {summary['robustness_class']}")
    print(f"Governança: {governance['governance_status']}")
    print(generate_options_walk_forward_report(summary, wf_results))
    print(generate_options_oos_governance_report(governance))
    if run_id:
        print(f"Run salvo: option_walk_forward_run_id={run_id}")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {"results": wf_results, "summary": summary, "context_summary": context_summary, "governance": governance, "run_id": run_id, "csv_paths": paths}


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward OOS de estruturas de opções.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--underlyings", nargs="*", default=None)
    parser.add_argument("--structure", default="LONG_CALL")
    parser.add_argument("--train-months", type=int, default=3)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--min-dte", type=int, default=7)
    parser.add_argument("--max-dte", type=int, default=90)
    parser.add_argument("--target-moneyness")
    parser.add_argument("--min-liquidity-score", type=float, default=0)
    parser.add_argument("--max-spread-pct", type=float, default=999)
    parser.add_argument("--holding-days", type=int, default=5)
    parser.add_argument("--cost-bps", type=float, default=10)
    parser.add_argument("--slippage-bps", type=float, default=5)
    parser.add_argument("--with-regimes", action="store_true")
    parser.add_argument("--with-events", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(**vars(args))


if __name__ == "__main__":
    main()

