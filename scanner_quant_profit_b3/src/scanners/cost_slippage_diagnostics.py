"""CLI de diagnóstico estrutural de custo e slippage."""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.cost_breakeven import calculate_cost_breakeven
from src.paper.cost_diagnostics_store import save_cost_diagnostics_run
from src.paper.cost_structure_diagnostics import analyze_cost_structure
from src.paper.liquidity_cost_diagnostics import analyze_liquidity_costs
from src.paper.paper_store import load_paper_equity_curve, load_paper_orders, load_paper_positions, load_paper_simulation_runs
from src.paper.turnover_diagnostics import analyze_turnover
from src.reports.cost_slippage_diagnostics_report import save_cost_slippage_diagnostics_markdown
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


def _load_market_data(db_path: Path, tickers: list[str] | None = None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    candidates = ["historical_prices", "cotahist_quotes", "b3_quotes"]
    try:
        with sqlite3.connect(db_path) as con:
            for table in candidates:
                if con.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (table,)).fetchone() is None:
                    continue
                df = pd.read_sql_query(f"SELECT * FROM {table}", con)
                if df.empty:
                    continue
                rename = {}
                if "date" in df.columns and "trade_date" not in df.columns:
                    rename["date"] = "trade_date"
                if "symbol" in df.columns and "ticker" not in df.columns:
                    rename["symbol"] = "ticker"
                if "volume_financeiro" in df.columns and "financial_volume" not in df.columns:
                    rename["volume_financeiro"] = "financial_volume"
                df = df.rename(columns=rename)
                if "ticker" in df.columns and tickers:
                    df = df[df["ticker"].astype(str).str.upper().isin({t.upper() for t in tickers})]
                return df
    except sqlite3.Error:
        return pd.DataFrame()
    return pd.DataFrame()


def _breakeven_input(db_path: Path, paper_run_id: int, cost_result: dict) -> pd.DataFrame:
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_cost_sensitivity_results'").fetchone():
                df = pd.read_sql_query("SELECT * FROM paper_cost_sensitivity_results WHERE run_id = ?", con, params=[int(paper_run_id)])
                if not df.empty:
                    return df.rename(columns={"mean_return": "total_return"})
    except sqlite3.Error:
        pass
    summary = cost_result.get("summary", {})
    gross = float(pd.to_numeric(pd.Series([summary.get("total_cost_drag", 0)]), errors="coerce").fillna(0).iloc[0])
    return pd.DataFrame(
        [
            {"scenario_name": "BASE_COST_ASSUMPTION", "cost_bps": 10, "slippage_bps": 5, "total_return": max(0.0, 0.01 - gross / 100000), "trades_count": 1},
            {"scenario_name": "STRESS_COST_ASSUMPTION", "cost_bps": 30, "slippage_bps": 20, "total_return": 0.01 - (gross * 2) / 100000, "trades_count": 1},
        ]
    )


def run(paper_run_id: int, save_db: bool = False, csv: bool = False, dry_run: bool = False, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    orders = load_paper_orders(db, run_id=paper_run_id)
    positions = load_paper_positions(db, run_id=paper_run_id)
    equity = load_paper_equity_curve(db, run_id=paper_run_id)
    tickers = sorted(orders.get("ticker", pd.Series(dtype=str)).dropna().astype(str).str.upper().unique().tolist()) if not orders.empty else []
    market = _load_market_data(db, tickers)
    cost = analyze_cost_structure(orders, positions)
    turnover = analyze_turnover(orders, equity)
    liquidity = analyze_liquidity_costs(orders, market)
    breakeven = calculate_cost_breakeven(_breakeven_input(db, paper_run_id, cost))
    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_cost_diagnostics_run(
            db,
            paper_run_id,
            cost["summary"],
            cost_by_ticker=cost["cost_by_ticker"],
            cost_by_signal_source=cost["cost_by_signal_source"],
            turnover_summary=turnover["summary"],
            breakeven_summary=breakeven,
            metadata={"dry_run": dry_run, "nao_recomendacao": True, "liquidity": liquidity.get("summary", {})},
        )
    csv_paths = {}
    if csv:
        csv_paths = {
            "cost_by_ticker": _write_csv(cost["cost_by_ticker"], "paper_cost_diagnostics_by_ticker"),
            "cost_by_signal_source": _write_csv(cost["cost_by_signal_source"], "paper_cost_diagnostics_by_signal_source"),
            "cost_by_exit_reason": _write_csv(cost["cost_by_exit_reason"], "paper_cost_diagnostics_by_exit_reason"),
            "turnover_by_ticker": _write_csv(turnover["turnover_by_ticker"], "paper_turnover_by_ticker"),
            "liquidity_by_ticker": _write_csv(liquidity["liquidity_by_ticker"], "paper_liquidity_cost_by_ticker"),
        }
    report_path = ""
    if csv or save_db:
        report_path = str(save_cost_slippage_diagnostics_markdown(_reports_dir() / f"cost_slippage_diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", cost, turnover, liquidity, breakeven))
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "paper_run_id": paper_run_id,
        "saved_run_id": saved_run_id,
        "cost_summary": cost["summary"],
        "turnover_summary": turnover["summary"],
        "liquidity_summary": liquidity["summary"],
        "breakeven": breakeven,
        "csv_paths": csv_paths,
        "report_path": report_path,
        "cost_result": cost,
        "turnover_result": turnover,
        "liquidity_result": liquidity,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnóstico estrutural de custo/slippage. Não recomendação.")
    parser.add_argument("--paper-run-id", type=int, required=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    summary = result["cost_summary"]
    print("COST SLIPPAGE DIAGNOSTICS")
    print(f"Status: {result['status']}")
    print(f"Paper run: {result['paper_run_id']}")
    print(f"Cost drag total: {summary.get('total_cost_drag', 0)}")
    print(f"Classe: {summary.get('cost_drag_class', 'INSUFFICIENT_DATA')}")
    print(f"Break-even custo bps: {result['breakeven'].get('max_cost_bps_supported', 0)}")
    if result["saved_run_id"]:
        print(f"Run salvo: {result['saved_run_id']}")
    if result["report_path"]:
        print(f"Relatório: {result['report_path']}")
    print("Não recomendação: diagnóstico e simulação, sem ordens reais e sem alteração de score/ranking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
