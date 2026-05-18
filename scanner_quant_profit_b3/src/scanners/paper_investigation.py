"""CLI de investigacoes analiticas sobre fragilidade do paper trading."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.investigation_comparison import compare_investigation_to_base
from src.paper.investigation_governance import evaluate_investigation_result
from src.paper.investigation_hypotheses import generate_hypotheses_from_fragility
from src.paper.investigation_simulator import run_investigation_simulation
from src.paper.investigation_store import save_investigation_run
from src.paper.paper_fragility_store import (
    load_paper_drawdown_periods,
    load_paper_fragility_by_asset,
    load_paper_fragility_by_signal_source,
    load_paper_fragility_runs,
)
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


def _load_row_by_id(db_path: Path, table: str, row_id: int) -> dict:
    if not db_path.exists():
        return {}
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                return {}
            df = pd.read_sql_query(f"SELECT * FROM {table} WHERE id = ?", con, params=(int(row_id),))
            return df.iloc[0].to_dict() if not df.empty else {}
    except sqlite3.Error:
        return {}


def _metadata(row: dict) -> dict:
    raw = row.get("metadata_json") or "{}"
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}


def _base_config(paper_run: dict) -> dict:
    metadata = _metadata(paper_run)
    return {
        "start_date": paper_run.get("start_date"),
        "end_date": paper_run.get("end_date"),
        "capital": float(paper_run.get("capital_initial") or 100000),
        "max_positions": int(metadata.get("max_positions", 5) or 5),
        "risk_pct": float(metadata.get("risk_pct", 0.005) or 0.005),
        "cost_bps": float(metadata.get("cost_bps", 10) or 10),
        "slippage_bps": float(metadata.get("slippage_bps", 5) or 5),
        "signal_source": metadata.get("signal_source", "quant"),
        "exit_mode": metadata.get("exit_mode", "advanced"),
        "enable_rebalancing": bool(metadata.get("enable_rebalancing", True)),
        "rebalance_frequency": metadata.get("rebalance_frequency", "WEEKLY"),
        "stop_loss_pct": float(metadata.get("stop_loss_pct", 0.03) or 0.03),
        "take_profit_pct": float(metadata.get("take_profit_pct", 0.10) or 0.10),
        "trailing_stop_pct": float(metadata.get("trailing_stop_pct", 0.04) or 0.04),
        "daily_loss_limit_pct": float(metadata.get("daily_loss_limit_pct", 0.02) or 0.02),
    }


def _base_summary(paper_run: dict, fragility_run: dict, asset_df: pd.DataFrame) -> dict:
    cost_drag = float(pd.to_numeric(asset_df.get("cost_drag"), errors="coerce").fillna(0).sum()) if asset_df is not None and not asset_df.empty else 0.0
    return {
        "total_return": paper_run.get("total_return", 0),
        "max_drawdown": paper_run.get("max_drawdown", 0),
        "profit_factor": paper_run.get("profit_factor", 0),
        "win_rate": paper_run.get("win_rate", 0),
        "trades_count": paper_run.get("trades_count", 0),
        "turnover": _metadata(paper_run).get("turnover", 0),
        "fragility_score": fragility_run.get("fragility_score", 100),
        "cost_drag": cost_drag,
        "governance_status": paper_run.get("governance_status"),
    }


def _load_inputs(db: Path, paper_run: dict, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    start = config.get("start_date")
    end = config.get("end_date")
    signal_source = str(config.get("signal_source") or "quant")
    signals = load_paper_signals(db, signal_source, start, end)
    tickers = sorted(signals["ticker"].dropna().astype(str).str.upper().unique().tolist()) if not signals.empty and "ticker" in signals.columns else None
    prices = _load_price_history(db, tickers, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    return signals, prices, risk


def run(
    paper_run_id: int,
    fragility_run_id: int,
    max_hypotheses: int | None = None,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    paper_run = _load_row_by_id(db, "paper_simulation_runs", paper_run_id)
    fragility_run = _load_row_by_id(db, "paper_fragility_runs", fragility_run_id)
    if not paper_run:
        return {"status": "INSUFFICIENT_DATA", "message": f"Paper run {paper_run_id} nao encontrado.", "results_df": pd.DataFrame(), "hypotheses_df": pd.DataFrame(), "saved_run_id": None, "csv_paths": {}}
    if not fragility_run:
        runs = load_paper_fragility_runs(db)
        fragility_run = runs.iloc[0].to_dict() if not runs.empty else {}

    asset_df = load_paper_fragility_by_asset(db, fragility_run_id)
    source_df = load_paper_fragility_by_signal_source(db, fragility_run_id)
    drawdown_df = load_paper_drawdown_periods(db, fragility_run_id)
    hypotheses = generate_hypotheses_from_fragility(asset_df, source_df, drawdown_df)
    if max_hypotheses:
        hypotheses = hypotheses.head(int(max_hypotheses))
    config = _base_config(paper_run)
    signals, prices, risk = _load_inputs(db, paper_run, config)
    base = _base_summary(paper_run, fragility_run, asset_df)
    rows = []
    if prices.empty or signals.empty:
        status = "INSUFFICIENT_DATA"
    else:
        status = "COMPLETED"
    for _, hyp in hypotheses.iterrows():
        if dry_run or prices.empty or signals.empty:
            sim = {
                "hypothesis_id": hyp.get("hypothesis_id"),
                "simulated_return": 0.0,
                "simulated_drawdown": 0.0,
                "simulated_trades": 0,
                "simulated_win_rate": 0.0,
                "simulated_profit_factor": 0.0,
                "fragility_score_after": base.get("fragility_score", 100),
                "governance_status": "DRY_RUN" if dry_run else "INSUFFICIENT_DATA",
                "metadata_json": json.dumps({"dry_run": dry_run}, ensure_ascii=False),
            }
        else:
            sim = run_investigation_simulation(config, hyp.to_dict(), signals, prices, risk)
        comparison = compare_investigation_to_base(base, sim)
        governance = evaluate_investigation_result(comparison)
        row = {
            "hypothesis_id": hyp.get("hypothesis_id"),
            "hypothesis_type": hyp.get("hypothesis_type"),
            "target": hyp.get("target"),
            "title": hyp.get("title"),
            "simulated_return": comparison["simulated_return"],
            "simulated_drawdown": comparison["simulated_drawdown"],
            "simulated_trades": comparison["simulated_trades"],
            "simulated_win_rate": comparison["simulated_win_rate"],
            "simulated_profit_factor": comparison["simulated_profit_factor"],
            "fragility_score_before": comparison["fragility_score_before"],
            "fragility_score_after": comparison["fragility_score_after"],
            "improvement_score": comparison["improvement_score"],
            "governance_status": governance["governance_status"],
            "conclusion": comparison["conclusion"],
            "metadata_json": json.dumps({"hypothesis": hyp.to_dict(), "comparison": comparison, "governance": governance}, ensure_ascii=False),
        }
        rows.append(row)
    results_df = pd.DataFrame(rows)
    improved = int(results_df["conclusion"].eq("INVESTIGATION_IMPROVED").sum()) if not results_df.empty else 0
    rejected = int(results_df["governance_status"].eq("INVESTIGATION_REJECTED").sum()) if not results_df.empty else 0
    observation = int(results_df["governance_status"].str.contains("OBSERVATION", na=False).sum()) if not results_df.empty else 0
    best = results_df.sort_values("improvement_score", ascending=False).head(1) if not results_df.empty else pd.DataFrame()
    summary = {
        "base_paper_run_id": paper_run_id,
        "base_fragility_run_id": fragility_run_id,
        "hypotheses_count": int(len(hypotheses)),
        "improved_count": improved,
        "rejected_count": rejected,
        "observation_count": observation,
        "best_hypothesis_id": None if best.empty else best.iloc[0]["hypothesis_id"],
        "best_improvement_score": None if best.empty else float(best.iloc[0]["improvement_score"]),
        "metadata": {"status": status, "base": base, "config": config, "dry_run": dry_run},
    }
    summary["metadata_json"] = json.dumps(summary["metadata"], ensure_ascii=False)
    saved_run_id = None
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved_run_id = save_investigation_run(db, summary, results_df)
    csv_paths = {}
    if csv:
        csv_paths = {
            "hypotheses": str(_write_csv(hypotheses, "paper_investigation_hypotheses") or ""),
            "results": str(_write_csv(results_df, "paper_investigation_results") or ""),
        }
    return {
        "status": status,
        "paper_run_id": paper_run_id,
        "fragility_run_id": fragility_run_id,
        "hypotheses_count": int(len(hypotheses)),
        "results_count": int(len(results_df)),
        "improved_count": improved,
        "best_hypothesis_id": summary["best_hypothesis_id"],
        "best_improvement_score": summary["best_improvement_score"],
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "hypotheses_df": hypotheses,
        "results_df": results_df,
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Investigacoes analiticas sobre fragilidade da carteira simulada.")
    parser.add_argument("--paper-run-id", type=int, required=True)
    parser.add_argument("--fragility-run-id", type=int, required=True)
    parser.add_argument("--max-hypotheses", type=int, default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("PAPER INVESTIGATION")
    print(f"Status: {summary['status']}")
    print(f"Paper run base: {summary['paper_run_id']}")
    print(f"Fragility run base: {summary['fragility_run_id']}")
    print(f"Hipoteses geradas: {summary['hypotheses_count']}")
    print(f"Experimentos simulados: {summary['results_count']}")
    print(f"Hipoteses com melhora: {summary['improved_count']}")
    print(f"Melhor hipotese: {summary['best_hypothesis_id']}")
    if summary["best_improvement_score"] is not None:
        print(f"Melhor improvement_score: {summary['best_improvement_score']:.2f}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    if summary["status"] == "INSUFFICIENT_DATA":
        print("Dados insuficientes para rodar investigacoes simuladas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
