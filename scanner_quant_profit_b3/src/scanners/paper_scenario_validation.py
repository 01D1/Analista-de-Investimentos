"""CLI de validacao multi-periodo e multi-fonte do paper trading."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.cost_scenario_analysis import analyze_cost_sensitivity, build_cost_scenarios
from src.paper.multi_period_validation import create_validation_periods, run_multi_period_validation, summarize_multi_period_validation
from src.paper.paper_scenario_governance import evaluate_multi_scenario_governance
from src.paper.paper_scenario_store import save_paper_scenario_validation_run
from src.paper.regime_scenario_validation import attach_regime_to_paper_results, summarize_paper_by_regime
from src.paper.scenario_model import build_default_paper_scenarios
from src.paper.signal_source_validation import compare_signal_sources
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


def _load_signals(db_path: str | Path, sources: list[str], start: str | None, end: str | None) -> pd.DataFrame:
    frames = [load_paper_signals(db_path, source, start, end) for source in sources]
    frames = [df for df in frames if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame(columns=["trade_date", "ticker", "signal_source"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(["trade_date", "ticker", "signal_source"])


def _load_regimes(db_path: str | Path, start: str | None, end: str | None) -> pd.DataFrame:
    if not Path(db_path).exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_regime_daily'").fetchone() is None:
                return pd.DataFrame()
            sql = "SELECT * FROM market_regime_daily"
            params = []
            where = []
            if start:
                where.append("trade_date >= ?")
                params.append(start)
            if end:
                where.append("trade_date <= ?")
                params.append(end)
            if where:
                sql += " WHERE " + " AND ".join(where)
            return pd.read_sql_query(sql, con, params=params)
    except sqlite3.Error:
        return pd.DataFrame()


def _build_scenarios(signal_sources: list[str], include_cost_scenarios: bool) -> pd.DataFrame:
    scenarios = build_default_paper_scenarios()
    wanted = {s.lower() for s in signal_sources}
    scenarios = scenarios[scenarios["signal_source"].astype(str).str.lower().isin(wanted)].copy()
    if include_cost_scenarios:
        costs = build_cost_scenarios()
        extra = []
        for _, row in costs.iterrows():
            extra.append(
                {
                    "scenario_id": row["scenario_id"],
                    "scenario_name": row["scenario_name"],
                    "signal_source": "quant" if "quant" in wanted else next(iter(wanted), "quant"),
                    "start_date": None,
                    "end_date": None,
                    "cost_bps": row["cost_bps"],
                    "slippage_bps": row["slippage_bps"],
                    "stop_loss_pct": 0.03,
                    "take_profit_pct": 0.10,
                    "trailing_stop_pct": 0.04,
                    "daily_loss_limit_pct": 0.02,
                    "max_positions": 5,
                    "risk_pct": 0.005,
                    "use_regime_adjustment": False,
                    "enable_rebalancing": False,
                    "metadata_json": "{}",
                }
            )
        scenarios = pd.concat([scenarios, pd.DataFrame(extra)], ignore_index=True)
    return scenarios.drop_duplicates(["scenario_id", "signal_source"]).reset_index(drop=True)


def run(
    start: str | None = None,
    end: str | None = None,
    capital: float = 100_000,
    signal_sources: list[str] | None = None,
    window_months: int = 3,
    step_months: int = 1,
    include_cost_scenarios: bool = False,
    include_regimes: bool = False,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    sources = signal_sources or ["quant", "technical", "integrated"]
    signals = _load_signals(db, sources, start, end)
    tickers = sorted(signals["ticker"].dropna().astype(str).unique().tolist()) if not signals.empty else None
    prices = _load_price_history(db, tickers, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    if start is None and not prices.empty:
        start = str(prices["trade_date"].min())
    if end is None and not prices.empty:
        end = str(prices["trade_date"].max())
    periods = create_validation_periods(start, end, window_months, step_months) if start and end else pd.DataFrame()
    scenarios = _build_scenarios(sources, include_cost_scenarios)
    results = run_multi_period_validation(signals, prices, risk, scenarios, periods, capital=capital)
    regimes = _load_regimes(db, start, end) if include_regimes else pd.DataFrame()
    regime_results = attach_regime_to_paper_results(results, regimes) if include_regimes else results
    regime_summary = summarize_paper_by_regime(regime_results) if include_regimes else pd.DataFrame()
    cost_df = analyze_cost_sensitivity(results)
    source_df = compare_signal_sources(results)
    summary = summarize_multi_period_validation(results)
    cost_classes = set(cost_df.get("cost_robustness_class", pd.Series(dtype=str)).astype(str).str.upper().tolist()) if not cost_df.empty else set()
    summary["cost_robustness_class"] = "COST_FRAGILE" if "COST_FRAGILE" in cost_classes else ("COST_SENSITIVE" if "COST_SENSITIVE" in cost_classes else "COST_ROBUST")
    summary["regime_fragile"] = bool(not regime_summary.empty and regime_summary["concentration_pct"].max() > 0.75)
    governance = evaluate_multi_scenario_governance(summary)
    run_summary = {
        "status": governance["governance_status"] if results.empty else "COMPLETED",
        "start_date": start,
        "end_date": end,
        "periods_count": summary["periods_count"],
        "scenarios_count": summary["scenarios_count"],
        "signal_sources_count": summary["signal_sources_count"],
        "positive_periods_pct": summary["positive_periods_pct"],
        "mean_return": summary["mean_return"],
        "mean_drawdown": summary["mean_drawdown"],
        "governance_status": governance["governance_status"],
        "metadata": {"summary": summary, "governance": governance, "dry_run": dry_run, "include_regimes": include_regimes},
    }
    run_summary["metadata_json"] = json.dumps(run_summary["metadata"], ensure_ascii=False, default=str)
    saved_run_id = None
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved_run_id = save_paper_scenario_validation_run(db, run_summary, results, cost_df, source_df)
    csv_paths = {}
    if csv:
        csv_paths = {
            "results": str(_write_csv(results, "paper_scenario_validation_results") or ""),
            "cost": str(_write_csv(cost_df, "paper_cost_sensitivity_results") or ""),
            "sources": str(_write_csv(source_df, "paper_signal_source_comparison") or ""),
            "regimes": str(_write_csv(regime_summary, "paper_regime_validation") or ""),
            "summary": str(_write_csv(pd.DataFrame([run_summary]), "paper_scenario_validation_summary") or ""),
        }
    return {
        "status": run_summary["status"],
        "signals_count": int(len(signals)),
        "periods_count": int(summary["periods_count"]),
        "scenarios_count": int(summary["scenarios_count"]),
        "mean_return": float(summary["mean_return"]),
        "positive_periods_pct": float(summary["positive_periods_pct"]),
        "governance_status": governance["governance_status"],
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "results_df": results,
        "cost_df": cost_df,
        "source_df": source_df,
        "regime_summary_df": regime_summary,
        "summary": run_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validacao multi-periodo e multi-cenario do paper trading.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--capital", type=float, default=100_000)
    parser.add_argument("--signal-sources", nargs="+", default=["quant", "technical", "integrated"])
    parser.add_argument("--window-months", type=int, default=3)
    parser.add_argument("--step-months", type=int, default=1)
    parser.add_argument("--include-cost-scenarios", action="store_true")
    parser.add_argument("--include-regimes", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("PAPER SCENARIO VALIDATION")
    print(f"Status: {summary['status']}")
    print(f"Sinais carregados: {summary['signals_count']}")
    print(f"Periodos: {summary['periods_count']}")
    print(f"Cenarios: {summary['scenarios_count']}")
    print(f"Retorno medio: {summary['mean_return']:.4f}")
    print(f"Periodos positivos: {summary['positive_periods_pct']:.2%}")
    print(f"Governanca multi-cenario: {summary['governance_status']}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    if summary["status"] == "PAPER_SCENARIO_BLOCKED_LOW_SAMPLE":
        print("Dados insuficientes para validacao multi-cenario robusta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
