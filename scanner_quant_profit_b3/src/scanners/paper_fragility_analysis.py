"""CLI de diagnostico de fragilidade da carteira simulada."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.cost_fragility import analyze_cost_drag_by_asset, analyze_cost_drag_by_scenario
from src.paper.drawdown_analysis import attribute_drawdown_to_positions, identify_drawdown_periods
from src.paper.fragility_by_asset import analyze_pnl_by_asset
from src.paper.fragility_by_signal_source import analyze_pnl_by_signal_source
from src.paper.fragility_score import calculate_fragility_score
from src.paper.paper_fragility_governance import evaluate_fragility_governance
from src.paper.paper_fragility_store import save_paper_fragility_run
from src.paper.paper_scenario_store import load_paper_scenario_validation_results
from src.paper.paper_store import load_paper_equity_curve, load_paper_orders, load_paper_positions
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


def _load_events(db_path: Path) -> pd.DataFrame:
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_events'").fetchone() is None:
                return pd.DataFrame()
            return pd.read_sql_query("SELECT * FROM market_events", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _summary(asset_df: pd.DataFrame, source_df: pd.DataFrame, drawdown_df: pd.DataFrame, paper_run_id: int) -> dict:
    total_trades = int(pd.to_numeric(asset_df.get("trades_count"), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0
    total_net_pnl = float(pd.to_numeric(asset_df.get("net_pnl"), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0.0
    top_conc = float(pd.to_numeric(asset_df.get("contribution_pct"), errors="coerce").abs().fillna(0).max()) if not asset_df.empty else 0.0
    cost_drag = float(pd.to_numeric(asset_df.get("total_cost_drag"), errors="coerce").fillna(0).sum()) if not asset_df.empty else 0.0
    cost_drag_pct = cost_drag / max(abs(total_net_pnl) + cost_drag, 1.0)
    max_dd = float(pd.to_numeric(drawdown_df.get("depth"), errors="coerce").fillna(0).min()) if not drawdown_df.empty else 0.0
    signal_fragile = bool(not source_df.empty and source_df["fragility_class"].astype(str).isin(["FRAGIL", "CRITICO", "DADOS_INSUFICIENTES"]).any())
    score = calculate_fragility_score({"trades_count": total_trades, "net_pnl": total_net_pnl, "cost_drag": cost_drag, "drawdown_contribution": abs(max_dd), "concentration_pct": top_conc, "win_rate": 0.5})
    fragility_summary = {
        "source_run_id": paper_run_id,
        "status": "COMPLETED" if total_trades else "PAPER_FRAGILITY_BLOCKED_DATA",
        "total_trades": total_trades,
        "total_net_pnl": round(total_net_pnl, 6),
        "fragility_score": score["fragility_score"],
        "fragility_class": score["fragility_class"],
        "cost_drag_pct": cost_drag_pct,
        "max_drawdown": max_dd,
        "top_asset_contribution_pct": top_conc,
        "signal_source_fragile": signal_fragile,
    }
    governance = evaluate_fragility_governance(fragility_summary)
    fragility_summary["governance_status"] = governance["governance_status"]
    fragility_summary["metadata"] = {"governance": governance, "cost_drag_pct": cost_drag_pct, "top_asset_contribution_pct": top_conc}
    fragility_summary["metadata_json"] = json.dumps(fragility_summary["metadata"], ensure_ascii=False)
    return fragility_summary


def run(
    paper_run_id: int | None = None,
    scenario_run_id: int | None = None,
    save_db: bool = False,
    csv: bool = False,
    include_regimes: bool = False,
    include_events: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    if paper_run_id is None:
        paper_run_id = 1
    orders = load_paper_orders(db, paper_run_id)
    positions = load_paper_positions(db, paper_run_id)
    equity = load_paper_equity_curve(db, paper_run_id)
    asset_df = analyze_pnl_by_asset(orders, positions, equity)
    source_df = analyze_pnl_by_signal_source(orders, positions)
    cost_asset_df = analyze_cost_drag_by_asset(orders)
    drawdown_df = identify_drawdown_periods(equity)
    drawdown_attr_df = attribute_drawdown_to_positions(drawdown_df, positions, orders)
    scenario_cost_df = pd.DataFrame()
    if scenario_run_id is not None:
        scenario_cost_df = analyze_cost_drag_by_scenario(load_paper_scenario_validation_results(db, scenario_run_id))
    summary = _summary(asset_df, source_df, drawdown_df, paper_run_id)
    saved_run_id = None
    if save_db:
        init_database(db, verbose=False)
        saved_run_id = save_paper_fragility_run(db, summary, asset_df, source_df, drawdown_df)
    csv_paths = {}
    if csv:
        csv_paths = {
            "asset": str(_write_csv(asset_df, "paper_fragility_by_asset") or ""),
            "signal_source": str(_write_csv(source_df, "paper_fragility_by_signal_source") or ""),
            "cost_asset": str(_write_csv(cost_asset_df, "paper_cost_fragility_by_asset") or ""),
            "scenario_cost": str(_write_csv(scenario_cost_df, "paper_cost_fragility_by_scenario") or ""),
            "drawdown": str(_write_csv(drawdown_df, "paper_drawdown_periods") or ""),
            "drawdown_attribution": str(_write_csv(drawdown_attr_df, "paper_drawdown_attribution") or ""),
            "summary": str(_write_csv(pd.DataFrame([summary]), "paper_fragility_summary") or ""),
        }
    return {
        "status": summary["status"],
        "paper_run_id": paper_run_id,
        "saved_run_id": saved_run_id,
        "total_trades": summary["total_trades"],
        "total_net_pnl": summary["total_net_pnl"],
        "fragility_score": summary["fragility_score"],
        "fragility_class": summary["fragility_class"],
        "governance_status": summary["governance_status"],
        "csv_paths": csv_paths,
        "asset_df": asset_df,
        "signal_source_df": source_df,
        "cost_asset_df": cost_asset_df,
        "drawdown_df": drawdown_df,
        "drawdown_attribution_df": drawdown_attr_df,
        "summary": summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnostico de fragilidade da carteira simulada.")
    parser.add_argument("--paper-run-id", type=int, default=None)
    parser.add_argument("--scenario-run-id", type=int, default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--include-regimes", action="store_true")
    parser.add_argument("--include-events", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("PAPER FRAGILITY ANALYSIS")
    print(f"Paper run: {summary['paper_run_id']}")
    print(f"Status: {summary['status']}")
    print(f"Trades: {summary['total_trades']}")
    print(f"P&L liquido simulado: {summary['total_net_pnl']:.2f}")
    print(f"Fragility score: {summary['fragility_score']:.2f}")
    print(f"Classe: {summary['fragility_class']}")
    print(f"Governanca: {summary['governance_status']}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
