"""CLI de simulacao de variantes para reducao de custos."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.cost_reduction_simulator import _metrics_from_result, run_cost_reduction_variants
from src.paper.cost_reduction_store import save_cost_reduction_run
from src.paper.exit_rule_variants import build_exit_rule_variants
from src.paper.paper_store import load_paper_equity_curve, load_paper_orders, load_paper_rebalance_events, load_paper_simulation_runs
from src.paper.rebalance_variants import build_rebalance_variants
from src.reports.cost_reduction_report import save_cost_reduction_report
from src.risk.risk_store import load_latest_risk_snapshots
from src.scanners.paper_trading_simulation import load_paper_signals
from src.scanners.risk_engine_snapshot import _load_price_history
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame, stem: str) -> str:
    if df is None or df.empty:
        return ""
    path = _reports_dir() / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return str(path)


def _run_row(db_path: Path, paper_run_id: int) -> dict:
    runs = load_paper_simulation_runs(db_path, limit=5000)
    if not runs.empty and "id" in runs.columns:
        row = runs[runs["id"].astype(int) == int(paper_run_id)]
        if not row.empty:
            return row.iloc[0].to_dict()
    return {}


def _metadata(row: dict) -> dict:
    try:
        return json.loads(row.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _base_config(db: Path, paper_run_id: int) -> dict:
    row = _run_row(db, paper_run_id)
    meta = _metadata(row)
    rebalance_events = load_paper_rebalance_events(db, run_id=paper_run_id)
    return {
        "start_date": row.get("start_date"),
        "end_date": row.get("end_date"),
        "capital": float(row.get("capital_initial") or 100000),
        "max_positions": int(meta.get("max_positions", 5) or 5),
        "risk_pct": float(meta.get("risk_pct", 0.005) or 0.005),
        "cost_bps": float(meta.get("cost_bps", 10) or 10),
        "slippage_bps": float(meta.get("slippage_bps", 5) or 5),
        "signal_source": meta.get("signal_source", "all"),
        "exit_mode": meta.get("exit_mode", "advanced"),
        "stop_loss_pct": meta.get("stop_loss_pct", 0.03),
        "take_profit_pct": meta.get("take_profit_pct", 0.06),
        "trailing_stop_pct": meta.get("trailing_stop_pct", 0.04),
        "atr_stop_multiplier": meta.get("atr_stop_multiplier"),
        "daily_loss_limit_pct": meta.get("daily_loss_limit_pct"),
        "weekly_loss_limit_pct": meta.get("weekly_loss_limit_pct"),
        "max_drawdown_pct": meta.get("max_drawdown_pct"),
        "enable_rebalancing": bool(meta.get("enable_rebalancing", not rebalance_events.empty)),
        "rebalance_frequency": meta.get("rebalance_frequency", "WEEKLY"),
        "use_regime_adjustment": bool(meta.get("use_regime_adjustment", False)),
        "close_positions_at_end": True,
    }


def _baseline_metrics_from_saved_run(db: Path, paper_run_id: int) -> dict | None:
    row = _run_row(db, paper_run_id)
    orders = load_paper_orders(db, run_id=paper_run_id)
    equity = load_paper_equity_curve(db, run_id=paper_run_id)
    if orders.empty:
        return None
    result = {"orders_df": orders, "equity_curve_df": equity, "performance_summary": row}
    return _metrics_from_result(result, variant_id="BASELINE_SAVED", variant_type="baseline")


def run(
    paper_run_id: int,
    variant_type: str = "all",
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    config = _base_config(db, paper_run_id)
    source = str(config.get("signal_source") or "all")
    signals = load_paper_signals(db, source, config.get("start_date"), config.get("end_date"))
    tickers = sorted(signals.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper().unique().tolist()) if not signals.empty else []
    prices = _load_price_history(db, tickers or None, config.get("start_date"), config.get("end_date"))
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    rebalance_variants = build_rebalance_variants() if variant_type in {"rebalance", "all"} else pd.DataFrame()
    exit_variants = build_exit_rule_variants() if variant_type in {"exit", "all"} else pd.DataFrame()
    baseline_metrics = _baseline_metrics_from_saved_run(db, paper_run_id)
    results = run_cost_reduction_variants(config, signals, prices, risk_df=risk, rebalance_variants=rebalance_variants, exit_rule_variants=exit_variants, baseline_metrics=baseline_metrics)
    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_cost_reduction_run(db, paper_run_id, results, metadata={"variant_type": variant_type, "dry_run": dry_run, "nao_recomendacao": True})
    csv_path = _write_csv(results, "cost_reduction_variants") if csv else ""
    report_path = ""
    if csv or save_db:
        report_path = str(save_cost_reduction_report(_reports_dir() / f"cost_reduction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", paper_run_id, results))
    best = results.iloc[0].to_dict() if not results.empty else {}
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "paper_run_id": paper_run_id,
        "variants_count": int(len(results)),
        "best_variant_id": best.get("variant_id"),
        "best_improvement_score": best.get("improvement_score"),
        "saved_run_id": saved_run_id,
        "csv_path": csv_path,
        "report_path": report_path,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulação de redução de custos. Não recomendação.")
    parser.add_argument("--paper-run-id", type=int, required=True)
    parser.add_argument("--variant-type", choices=["rebalance", "exit", "all"], default="all")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print("COST REDUCTION SIMULATION")
    print(f"Status: {result['status']}")
    print(f"Paper run base: {result['paper_run_id']}")
    print(f"Variantes simuladas: {result['variants_count']}")
    print(f"Melhor variante: {result.get('best_variant_id') or '-'}")
    print(f"Melhor score: {result.get('best_improvement_score') or 0}")
    if result.get("saved_run_id"):
        print(f"Run salvo: {result['saved_run_id']}")
    if result.get("csv_path"):
        print(f"CSV: {result['csv_path']}")
    if result.get("report_path"):
        print(f"Relatório: {result['report_path']}")
    print("Não recomendação: variante simulada, sem ordens reais e sem aplicação automática.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
