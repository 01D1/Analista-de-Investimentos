"""CLI de walk-forward das regras simuladas de paper trading."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.exit_parameter_optimizer import grid_search_exit_parameters, rank_exit_parameter_results
from src.paper.paper_oos_governance import evaluate_paper_oos_governance
from src.paper.paper_walk_forward import run_paper_walk_forward, summarize_paper_walk_forward
from src.paper.paper_walk_forward_store import save_paper_walk_forward_run
from src.risk.risk_store import load_latest_risk_snapshots
from src.scanners.paper_trading_simulation import load_paper_signals
from src.scanners.risk_engine_snapshot import _load_price_history
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame, stem: str) -> Path | None:
    if df is None or df.empty:
        return None
    path = _reports_dir() / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def run(
    start: str | None = None,
    end: str | None = None,
    capital: float = 100_000,
    signal_source: str = "quant",
    train_months: int = 2,
    test_months: int = 1,
    objective: str = "total_return",
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    signals = load_paper_signals(db, signal_source, start, end)
    tickers = sorted(signals["ticker"].dropna().astype(str).unique().tolist()) if not signals.empty else None
    prices = _load_price_history(db, tickers, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    wf_results = run_paper_walk_forward(
        signals,
        prices,
        risk_df=risk,
        train_months=train_months,
        test_months=test_months,
        objective=objective,
        capital=capital,
    )
    wf_summary = summarize_paper_walk_forward(wf_results)
    governance = evaluate_paper_oos_governance(wf_summary)
    wf_summary.update(
        {
            "status": "COMPLETED" if not wf_results.empty else "PAPER_WF_DADOS_INSUFICIENTES",
            "start_date": start,
            "end_date": end,
            "train_months": train_months,
            "test_months": test_months,
            "governance_status": governance["governance_status"],
            "metadata": {"objective": objective, "signal_source": signal_source, "capital": capital, "governance": governance, "dry_run": dry_run},
        }
    )
    wf_summary["metadata_json"] = json.dumps(wf_summary["metadata"], ensure_ascii=False)
    opt_results = pd.DataFrame()
    if not signals.empty and not prices.empty:
        opt_results = rank_exit_parameter_results(grid_search_exit_parameters(signals, prices, risk_df=risk, objective=objective, capital=capital))
    saved_run_id = None
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved_run_id = save_paper_walk_forward_run(db, wf_summary, wf_results, opt_results)
    csv_paths = {}
    if csv:
        csv_paths = {
            "walk_forward": str(_write_csv(wf_results, "paper_walk_forward_results") or ""),
            "optimization": str(_write_csv(opt_results, "paper_exit_optimization_results") or ""),
            "summary": str(_write_csv(pd.DataFrame([wf_summary]), "paper_walk_forward_summary") or ""),
        }
    return {
        "status": wf_summary["status"],
        "signals_count": int(len(signals)),
        "windows_count": int(wf_summary["windows_count"]),
        "positive_windows_pct": float(wf_summary["positive_windows_pct"]),
        "mean_test_return": float(wf_summary["mean_test_return"]),
        "robustness_class": wf_summary["robustness_class"],
        "governance_status": governance["governance_status"],
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "results_df": wf_results,
        "optimization_df": opt_results,
        "summary": wf_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Walk-forward de regras simuladas de paper trading.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--capital", type=float, default=100_000)
    parser.add_argument("--signal-source", choices=["integrated", "technical", "quant", "all"], default="quant")
    parser.add_argument("--train-months", type=int, default=2)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--objective", default="total_return")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("PAPER RULES WALK-FORWARD")
    print(f"Status: {summary['status']}")
    print(f"Sinais carregados: {summary['signals_count']}")
    print(f"Janelas: {summary['windows_count']}")
    print(f"Janelas positivas: {summary['positive_windows_pct']:.2%}")
    print(f"Retorno medio OOS: {summary['mean_test_return']:.4f}")
    print(f"Robustez: {summary['robustness_class']}")
    print(f"Governanca OOS: {summary['governance_status']}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    if summary["status"] == "PAPER_WF_DADOS_INSUFICIENTES":
        print("Dados insuficientes para robustez fora da amostra das regras simuladas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
