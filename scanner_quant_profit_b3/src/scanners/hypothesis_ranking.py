"""CLI de ranking multi-fonte de hipóteses em paper trading."""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.hypothesis_multi_source_validation import run_hypothesis_multi_source_validation
from src.paper.hypothesis_ranking import generate_hypothesis_ranking_report, rank_hypotheses
from src.paper.hypothesis_ranking_store import save_hypothesis_ranking_run
from src.paper.hypothesis_universe import build_default_hypothesis_universe
from src.risk.risk_store import load_latest_risk_snapshots
from src.scanners.risk_engine_snapshot import _load_price_history
from src.signals.signal_source_unifier import (
    load_integrated_signals_for_paper,
    load_quant_signals_for_paper,
    load_technical_signals_for_paper,
)
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


def _load_regimes(db_path: Path, start: str | None, end: str | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_regime_daily'").fetchone() is None:
                return pd.DataFrame()
            df = pd.read_sql_query("SELECT * FROM market_regime_daily", con)
    except sqlite3.Error:
        return pd.DataFrame()
    if df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    df["trade_date"] = df["trade_date"].astype(str)
    if start:
        df = df[df["trade_date"] >= str(start)]
    if end:
        df = df[df["trade_date"] <= str(end)]
    return df


def _signals_by_source(db: Path, sources: list[str], start: str | None, end: str | None) -> dict[str, pd.DataFrame]:
    loaders = {
        "quant": load_quant_signals_for_paper,
        "technical": load_technical_signals_for_paper,
        "integrated": load_integrated_signals_for_paper,
    }
    out = {}
    for source in sources:
        key = str(source).lower()
        loader = loaders.get(key)
        if loader:
            out[key] = loader(db, start, end)
    return out


def run(
    start: str | None = None,
    end: str | None = None,
    sources: list[str] | None = None,
    train_months: int = 1,
    test_months: int = 1,
    include_cost_scenarios: bool = False,
    include_regimes: bool = False,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    sources = [s.lower() for s in (sources or ["quant", "technical", "integrated"])]
    hypotheses = build_default_hypothesis_universe()
    signals = _signals_by_source(db, sources, start, end)
    tickers = sorted({ticker for df in signals.values() if df is not None and not df.empty for ticker in df["ticker"].dropna().astype(str).str.upper().tolist()})
    prices = _load_price_history(db, tickers or None, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    regimes = _load_regimes(db, start, end) if include_regimes else pd.DataFrame()
    validation = run_hypothesis_multi_source_validation(
        hypotheses,
        signals,
        prices,
        risk_df=risk,
        regimes_df=regimes,
        start_date=start,
        end_date=end,
        train_months=train_months,
        test_months=test_months,
        cost_scenarios=include_cost_scenarios,
    )
    ranked = rank_hypotheses(validation)
    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_hypothesis_ranking_run(
            db,
            ranked,
            validation,
            metadata={
                "sources": sources,
                "start": start,
                "end": end,
                "dry_run": dry_run,
                "include_cost_scenarios": include_cost_scenarios,
                "include_regimes": include_regimes,
            },
        )
    csv_paths = {}
    if csv:
        csv_paths = {
            "results": _write_csv(ranked, "hypothesis_ranking_results"),
            "summary": _write_csv(validation, "hypothesis_ranking_summary"),
        }
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "hypotheses_count": int(len(hypotheses)),
        "validation_rows": int(len(validation)),
        "ranked_rows": int(len(ranked)),
        "best_hypothesis_id": str(ranked.iloc[0]["hypothesis_id"]) if not ranked.empty else "",
        "best_score": float(ranked.iloc[0]["hypothesis_robustness_score"]) if not ranked.empty else 0.0,
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "report": generate_hypothesis_ranking_report(ranked),
        "hypotheses_df": hypotheses,
        "validation_df": validation,
        "ranked_df": ranked,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ranking multi-fonte de hipóteses em estudo. Não recomendação.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--sources", nargs="+", default=["quant", "technical", "integrated"])
    parser.add_argument("--train-months", type=int, default=1)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--include-cost-scenarios", action="store_true")
    parser.add_argument("--include-regimes", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(**vars(args))
    print("HYPOTHESIS RANKING")
    print(f"Status: {result['status']}")
    print(f"Hipóteses testadas: {result['hypotheses_count']}")
    print(f"Linhas de validação: {result['validation_rows']}")
    print(f"Ranking gerado: {result['ranked_rows']}")
    print(f"Melhor hipótese em estudo: {result['best_hypothesis_id']} ({result['best_score']:.2f})")
    if result["saved_run_id"]:
        print(f"Run salvo: {result['saved_run_id']}")
    if result["csv_paths"]:
        print(f"CSVs: {result['csv_paths']}")
    print("Não recomendação: ranking é simulação, investigação e validação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

