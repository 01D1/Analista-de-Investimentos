"""CLI de validacao OOS/multi-cenario de hipoteses de investigacao."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.paper.hypothesis_oos_governance import evaluate_hypothesis_oos_governance
from src.paper.hypothesis_oos_store import save_hypothesis_oos_run
from src.paper.hypothesis_oos_validation import run_hypothesis_oos_validation, summarize_hypothesis_oos_validation
from src.paper.hypothesis_oos_coverage import (
    compare_coverage_before_after,
    diagnose_oos_coverage,
    filter_scenarios_by_coverage,
    load_expanded_paper_signals,
    summarize_coverage,
    summarize_source_coverage_requirements,
)
from src.paper.hypothesis_validation_model import build_hypothesis_validation_scenarios
from src.paper.investigation_store import load_investigation_results, load_investigation_runs
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


def _json(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _load_regimes(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_regime_daily'").fetchone() is None:
                return pd.DataFrame()
            return pd.read_sql_query("SELECT * FROM market_regime_daily", con)
    except sqlite3.Error:
        return pd.DataFrame()


def _load_hypothesis(db_path: Path, investigation_run_id: int | None, hypothesis_id: str | None, hypothesis_type: str | None, target: str | None) -> dict:
    if investigation_run_id is not None:
        results = load_investigation_results(db_path, run_id=investigation_run_id)
        if hypothesis_id:
            results = results[results["hypothesis_id"].astype(str) == str(hypothesis_id)]
        if not results.empty:
            row = results.iloc[0].to_dict()
            metadata = _json(row.get("metadata_json"))
            hyp = metadata.get("hypothesis") if isinstance(metadata, dict) else None
            if isinstance(hyp, dict):
                return hyp
            return {"hypothesis_id": row.get("hypothesis_id"), "hypothesis_type": row.get("hypothesis_type"), "target": row.get("target"), "metadata_json": row.get("metadata_json", "{}")}
    return {
        "hypothesis_id": hypothesis_id or "REDUCE_VOLATILITY_EXPOSURE",
        "hypothesis_type": hypothesis_type or "REDUCE_VOLATILITY_EXPOSURE",
        "target": target or "portfolio",
        "metadata_json": "{}",
    }


def _date_bounds(db_path: Path, start: str | None, end: str | None, investigation_run_id: int | None) -> tuple[str | None, str | None]:
    if start and end:
        return start, end
    if investigation_run_id is not None:
        runs = load_investigation_runs(db_path)
        matches = runs[runs["id"].astype(int) == int(investigation_run_id)] if not runs.empty else pd.DataFrame()
        if not matches.empty:
            meta = _json(matches.iloc[0].get("metadata_json"))
            config = meta.get("config", {}) if isinstance(meta, dict) else {}
            start = start or config.get("start_date")
            end = end or config.get("end_date")
    return start, end


def _filter_scenarios(scenarios: pd.DataFrame, signal_sources: list[str], include_cost_scenarios: bool, include_regimes: bool) -> pd.DataFrame:
    if scenarios.empty:
        return scenarios
    allowed_sources = {s.lower() for s in signal_sources}
    out = scenarios[scenarios["signal_source"].astype(str).str.lower().isin(allowed_sources)].copy()
    base_names = {"BASE_COST", "LOW_RISK", "HIGH_RISK", "QUANT_ONLY", "TECHNICAL_ONLY", "INTEGRATED_ONLY"}
    if include_cost_scenarios:
        base_names |= {"HIGH_COST", "HIGH_SLIPPAGE"}
    if include_regimes:
        base_names |= {"REGIME_LATERAL", "REGIME_ALTA_TENDENCIAL", "REGIME_ALTA_VOLATILIDADE"}
    out = out[out["scenario_name"].isin(base_names)].copy()
    return out if not out.empty else scenarios.head(1).copy()


def run(
    investigation_run_id: int | None = None,
    hypothesis_id: str | None = "REDUCE_VOLATILITY_EXPOSURE",
    hypothesis_type: str | None = None,
    target: str | None = None,
    start: str | None = None,
    end: str | None = None,
    train_months: int = 2,
    test_months: int = 1,
    include_cost_scenarios: bool = False,
    include_regimes: bool = False,
    signal_sources: list[str] | None = None,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    expand_signal_coverage: bool = False,
    filter_coverage: bool = False,
    require_source_coverage: bool = False,
    min_useful_coverage_pct: float = 0.5,
    min_signals_per_source: int = 30,
    min_signals_per_window: int = 1,
    min_price_days_per_window: int = 5,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    signal_sources = signal_sources or ["quant"]
    if require_source_coverage and signal_sources == ["quant"]:
        signal_sources = ["quant", "technical", "integrated"]
        expand_signal_coverage = True
    hypothesis = _load_hypothesis(db, investigation_run_id, hypothesis_id, hypothesis_type, target)
    start, end = _date_bounds(db, start, end, investigation_run_id)
    base_signals = load_paper_signals(db, "all", start, end)
    signals = load_expanded_paper_signals(db, signal_sources, start, end) if expand_signal_coverage else base_signals
    tickers = sorted(signals["ticker"].dropna().astype(str).str.upper().unique().tolist()) if not signals.empty and "ticker" in signals.columns else None
    prices = _load_price_history(db, tickers, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    regimes = _load_regimes(db) if include_regimes else pd.DataFrame()
    if start is None and not prices.empty:
        start = str(prices["trade_date"].astype(str).min())
    if end is None and not prices.empty:
        end = str(prices["trade_date"].astype(str).max())
    scenarios = build_hypothesis_validation_scenarios(pd.DataFrame([hypothesis]), start or "", end or "")
    scenarios = _filter_scenarios(scenarios, signal_sources, include_cost_scenarios, include_regimes)
    coverage_before = diagnose_oos_coverage(
        base_signals,
        prices,
        regimes,
        scenarios,
        start or "",
        end or "",
        train_months=train_months,
        test_months=test_months,
        min_signals_per_window=min_signals_per_window,
        min_price_days_per_window=min_price_days_per_window,
    )
    coverage_after = diagnose_oos_coverage(
        signals,
        prices,
        regimes,
        scenarios,
        start or "",
        end or "",
        train_months=train_months,
        test_months=test_months,
        min_signals_per_window=min_signals_per_window,
        min_price_days_per_window=min_price_days_per_window,
    )
    coverage_comparison = compare_coverage_before_after(coverage_before, coverage_after)
    coverage_summary = summarize_coverage(coverage_after)
    if filter_coverage:
        scenarios = filter_scenarios_by_coverage(scenarios, coverage_after)
        coverage_after = diagnose_oos_coverage(
            signals,
            prices,
            regimes,
            scenarios,
            start or "",
            end or "",
            train_months=train_months,
            test_months=test_months,
            min_signals_per_window=min_signals_per_window,
            min_price_days_per_window=min_price_days_per_window,
        )
        coverage_summary = summarize_coverage(coverage_after)
        coverage_comparison = compare_coverage_before_after(coverage_before, coverage_after)
    source_requirements = summarize_source_coverage_requirements(
        coverage_after,
        min_useful_coverage_pct=min_useful_coverage_pct,
        min_signals_per_source=min_signals_per_source,
    ) if require_source_coverage else {
        "requirements_status": "COVERAGE_NOT_REQUIRED",
        "excluded_sources": [],
        "passed_sources": sorted({str(s).lower() for s in signal_sources}),
        "source_summary": [],
        "message": "Cobertura mínima por fonte não exigida neste run.",
    }
    excluded_sources = set(source_requirements.get("excluded_sources", []))
    if require_source_coverage and excluded_sources:
        scenarios = scenarios[~scenarios["signal_source"].astype(str).str.lower().isin(excluded_sources)].copy()
        if scenarios.empty:
            coverage_summary["coverage_status"] = "COVERAGE_INSUFFICIENT"
    coverage_blocked = bool(
        require_source_coverage
        and (
            source_requirements.get("requirements_status") == "COVERAGE_INSUFFICIENT"
            or float(coverage_summary.get("useful_cells_pct") or 0) < float(min_useful_coverage_pct)
        )
    )
    if dry_run or signals.empty or prices.empty or coverage_blocked:
        results_df = pd.DataFrame()
        summary = summarize_hypothesis_oos_validation(results_df)
        status = "DRY_RUN" if dry_run else "COVERAGE_INSUFFICIENT" if coverage_blocked else "HYPOTHESIS_INSUFFICIENT_DATA"
    else:
        results_df = run_hypothesis_oos_validation(
            hypothesis,
            signals,
            prices,
            risk_df=risk,
            regimes_df=regimes,
            train_months=train_months,
            test_months=test_months,
            scenarios=scenarios,
        )
        summary = summarize_hypothesis_oos_validation(results_df)
        status = summary["robustness_class"]
    governance = evaluate_hypothesis_oos_governance(summary)
    run_summary = {
        **summary,
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "hypothesis_type": hypothesis.get("hypothesis_type"),
        "target": hypothesis.get("target"),
        "governance_status": governance["governance_status"],
        "metadata": {
            "hypothesis": hypothesis,
            "governance": governance,
            "status": status,
            "scenarios": scenarios.to_dict("records"),
            "dry_run": dry_run,
            "coverage_summary": coverage_summary,
            "coverage_comparison": coverage_comparison,
            "expand_signal_coverage": expand_signal_coverage,
            "filter_coverage": filter_coverage,
            "require_source_coverage": require_source_coverage,
            "source_coverage_requirements": source_requirements,
            "excluded_sources_by_coverage": sorted(excluded_sources),
        },
    }
    run_summary["metadata_json"] = json.dumps(run_summary["metadata"], ensure_ascii=False, default=str)
    saved_run_id = None
    if save_db and not dry_run:
        init_database(db, verbose=False)
        saved_run_id = save_hypothesis_oos_run(db, run_summary, results_df, coverage_after)
    csv_paths = {}
    if csv:
        csv_paths = {
            "results": str(_write_csv(results_df, "hypothesis_oos_results") or ""),
            "summary": str(_write_csv(pd.DataFrame([run_summary]), "hypothesis_oos_summary") or ""),
            "coverage_before": str(_write_csv(coverage_before, "hypothesis_oos_coverage_before") or ""),
            "coverage_after": str(_write_csv(coverage_after, "hypothesis_oos_coverage_after") or ""),
            "coverage_comparison": str(_write_csv(pd.DataFrame([coverage_comparison]), "hypothesis_oos_coverage_comparison") or ""),
        }
    return {
        "status": status,
        "hypothesis_id": hypothesis.get("hypothesis_id"),
        "robustness_class": summary["robustness_class"],
        "governance_status": governance["governance_status"],
        "windows_count": summary["windows_count"],
        "scenarios_count": summary["scenarios_count"],
        "positive_improvement_pct": summary["positive_improvement_pct"],
        "mean_return_delta": summary["mean_return_delta"],
        "mean_drawdown_delta": summary["mean_drawdown_delta"],
        "mean_fragility_delta": summary["mean_fragility_delta"],
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "results_df": results_df,
        "coverage_df": coverage_after,
        "coverage_summary": coverage_summary,
        "coverage_comparison": coverage_comparison,
        "source_coverage_requirements": source_requirements,
        "excluded_sources_by_coverage": sorted(excluded_sources),
        "summary": run_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validacao OOS/multi-cenario de hipoteses de investigacao.")
    parser.add_argument("--investigation-run-id", type=int, default=None)
    parser.add_argument("--hypothesis-id", default="REDUCE_VOLATILITY_EXPOSURE")
    parser.add_argument("--hypothesis-type", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--train-months", type=int, default=2)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--include-cost-scenarios", action="store_true")
    parser.add_argument("--include-regimes", action="store_true")
    parser.add_argument("--signal-sources", nargs="+", default=["quant"])
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expand-signal-coverage", action="store_true")
    parser.add_argument("--filter-coverage", action="store_true")
    parser.add_argument("--require-source-coverage", action="store_true")
    parser.add_argument("--min-useful-coverage-pct", type=float, default=0.5)
    parser.add_argument("--min-signals-per-source", type=int, default=30)
    parser.add_argument("--min-signals-per-window", type=int, default=1)
    parser.add_argument("--min-price-days-per-window", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("HYPOTHESIS OOS VALIDATION")
    print(f"Hipotese: {summary['hypothesis_id']}")
    print(f"Status: {summary['status']}")
    print(f"Robustez: {summary['robustness_class']}")
    print(f"Governanca: {summary['governance_status']}")
    print(f"Janelas: {summary['windows_count']}")
    print(f"Cenarios: {summary['scenarios_count']}")
    print(f"Melhora positiva: {summary['positive_improvement_pct']:.4f}")
    print(f"Delta retorno medio: {summary['mean_return_delta']:.6f}")
    print(f"Delta drawdown medio: {summary['mean_drawdown_delta']:.6f}")
    print(f"Delta fragilidade medio: {summary['mean_fragility_delta']:.6f}")
    if summary.get("coverage_summary"):
        cov = summary["coverage_summary"]
        print(f"Cobertura util: {cov.get('useful_cells', 0)}/{cov.get('coverage_cells', 0)} ({cov.get('useful_cells_pct', 0):.4f})")
    if summary.get("source_coverage_requirements"):
        req = summary["source_coverage_requirements"]
        print(f"Cobertura por fonte: {req.get('requirements_status')}")
        if req.get("excluded_sources"):
            print(f"Fontes excluidas por cobertura insuficiente: {', '.join(req.get('excluded_sources'))}")
    if summary["saved_run_id"]:
        print(f"Run salvo: {summary['saved_run_id']}")
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
