"""CLI de walk-forward técnico fora da amostra."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.quant.historical_loader import load_daily_prices
from src.scanners.technical_analysis_scanner import _prepare_setups, build_technical_features
from src.technical.setup_deduplication import deduplicate_setups
from src.technical.technical_backtest import run_technical_setup_backtest
from src.technical.technical_context_analysis import (
    attach_event_context_to_technical_results,
    attach_regime_to_technical_results,
    generate_technical_context_report,
    summarize_technical_by_event_context,
    summarize_technical_by_regime,
)
from src.technical.technical_oos_governance import evaluate_technical_oos_candidate, generate_technical_oos_governance_report
from src.technical.technical_threshold_optimizer import generate_technical_threshold_report, grid_search_technical_thresholds, rank_technical_threshold_results
from src.technical.technical_walk_forward import generate_technical_walk_forward_report, run_technical_walk_forward, summarize_technical_walk_forward
from src.technical.technical_walk_forward_store import save_technical_walk_forward_run
from src.utils import load_config, project_path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_table(db_path: Path, table: str) -> pd.DataFrame:
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


def _backtest_input(features: pd.DataFrame, setups: pd.DataFrame) -> pd.DataFrame:
    if features.empty or setups.empty:
        return pd.DataFrame()
    labels = setups[["trade_date", "ticker", "setup_type", "setup_score", "setup_confidence", "setup_direction"]].copy()
    labels["trade_date"] = pd.to_datetime(labels["trade_date"], errors="coerce").dt.date.astype(str)
    base = features.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.date.astype(str)
    return base.merge(labels, on=["trade_date", "ticker"], how="left")


def _write_csv(results: pd.DataFrame, thresholds: pd.DataFrame, dedup_summary: dict) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "walk_forward": reports / f"technical_walk_forward_results_{stamp}.csv",
        "thresholds": reports / f"technical_threshold_optimization_{stamp}.csv",
        "dedup": reports / f"technical_setup_dedup_{stamp}.csv",
    }
    results.to_csv(paths["walk_forward"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    thresholds.to_csv(paths["thresholds"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    pd.DataFrame([dedup_summary]).to_csv(paths["dedup"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def _save_auxiliary(db: Path, start: str | None, end: str | None, objective: str, thresholds: pd.DataFrame, dedup_summary: dict) -> None:
    with sqlite3.connect(db) as con:
        if not thresholds.empty:
            best = rank_technical_threshold_results(thresholds, objective).iloc[0]
            con.execute(
                """
                INSERT INTO technical_threshold_optimization_runs (
                    created_at, start_date, end_date, objective, best_params_json,
                    best_mean_return, best_hit_rate, best_samples, overfitting_warning, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    start,
                    end,
                    objective,
                    best.get("params_json"),
                    float(best.get("mean_return_5d") or 0),
                    float(best.get("hit_rate_5d") or 0),
                    int(best.get("signals_count") or 0),
                    best.get("overfitting_risk_hint"),
                    "{}",
                ),
            )
        if dedup_summary:
            con.execute(
                """
                INSERT INTO technical_setup_dedup_runs (
                    created_at, signals_before, signals_after, removed_count,
                    removed_pct, top_redundant_setups_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _now(),
                    int(dedup_summary.get("signals_before") or 0),
                    int(dedup_summary.get("signals_after") or 0),
                    int(dedup_summary.get("removed_count") or 0),
                    float(dedup_summary.get("removed_pct") or 0),
                    json.dumps(dedup_summary.get("top_redundant_setups", {}), ensure_ascii=False),
                    json.dumps(dedup_summary, ensure_ascii=False),
                ),
            )
        con.commit()


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    setup_type: str | None = None,
    train_months: int = 3,
    test_months: int = 1,
    objective: str = "mean_return_5d",
    dedupe: bool = False,
    optimize_thresholds: bool = False,
    with_regimes: bool = False,
    with_events: bool = False,
    save_db: bool = False,
    write_csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = _now()
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    prices = load_daily_prices(db, tickers=tickers, start_date=start, end_date=end)
    if prices.empty:
        features = pd.DataFrame()
        setups = pd.DataFrame()
        backtest = pd.DataFrame()
        results = pd.DataFrame()
        thresholds = pd.DataFrame()
        dedup_summary = {"signals_before": 0, "signals_after": 0, "removed_count": 0, "removed_pct": 0.0}
    else:
        features = build_technical_features(prices)
        setups = _prepare_setups(features, [setup_type] if setup_type else None, None)
        dedup_summary = {"signals_before": len(setups), "signals_after": len(setups), "removed_count": 0, "removed_pct": 0.0}
        if dedupe:
            setups, _removed, dedup_summary = deduplicate_setups(setups)
        bt_input = _backtest_input(features, setups)
        backtest = run_technical_setup_backtest(bt_input)
        if with_regimes and not backtest.empty:
            backtest = attach_regime_to_technical_results(backtest, _read_table(db, "market_regime_daily"))
        if with_events and not backtest.empty:
            backtest = attach_event_context_to_technical_results(backtest, _read_table(db, "market_events"))
        thresholds = grid_search_technical_thresholds(backtest, objective=objective) if optimize_thresholds else pd.DataFrame()
        results = run_technical_walk_forward(features, setups, backtest, train_months=train_months, test_months=test_months, objective=objective)
    summary = summarize_technical_walk_forward(results)
    governance = evaluate_technical_oos_candidate(summary)
    regime_summary = summarize_technical_by_regime(backtest)
    event_summary = summarize_technical_by_event_context(backtest)
    finished = _now()
    run_summary = {
        **summary,
        "started_at": started,
        "finished_at": finished,
        "status": "SUCCESS" if summary["windows_count"] else "TECH_WF_DADOS_INSUFICIENTES",
        "start_date": start,
        "end_date": end,
        "train_months": train_months,
        "test_months": test_months,
        "setup_type": setup_type,
        "governance_status": governance["governance_status"],
        "metadata": {"tickers": tickers or [], "dedupe": dedup_summary, "context_report": generate_technical_context_report(regime_summary, event_summary)},
    }
    paths = _write_csv(results, rank_technical_threshold_results(thresholds, objective) if not thresholds.empty else thresholds, dedup_summary) if write_csv else {}
    run_id = None
    if save_db and not dry_run:
        run_id = save_technical_walk_forward_run(db, run_summary, results)
        _save_auxiliary(db, start, end, objective, thresholds, dedup_summary)

    print("\nTECHNICAL WALK-FORWARD ANALYSIS")
    print(f"Status: {run_summary['status']}")
    print(f"Janelas: {summary['windows_count']}")
    print(f"Janelas positivas: {summary['positive_windows_pct']}%")
    print(f"Retorno médio teste D+5: {summary['mean_test_return']}%")
    print(f"Robustez: {summary['robustness_class']}")
    print(f"Governança OOS: {governance['governance_status']}")
    print(f"Deduplicação: {dedup_summary.get('signals_before', 0)} -> {dedup_summary.get('signals_after', 0)} sinais")
    print(generate_technical_walk_forward_report(summary, results))
    print(generate_technical_oos_governance_report(governance))
    if optimize_thresholds:
        print(generate_technical_threshold_report(thresholds))
    if run_id:
        print(f"Run salvo: technical_walk_forward_run_id={run_id}")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {
        "features": features,
        "setups": setups,
        "backtest": backtest,
        "results": results,
        "summary": summary,
        "thresholds": thresholds,
        "dedup_summary": dedup_summary,
        "governance": governance,
        "run_id": run_id,
        "csv_paths": paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward técnico OOS.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--setup-type")
    parser.add_argument("--train-months", type=int, default=3)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--objective", default="mean_return_5d")
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--optimize-thresholds", action="store_true")
    parser.add_argument("--with-regimes", action="store_true")
    parser.add_argument("--with-events", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(**vars(args))


if __name__ == "__main__":
    main()

