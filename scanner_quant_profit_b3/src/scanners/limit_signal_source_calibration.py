"""CLI de calibração paramétrica LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.limit_signal_source_oos import run_limit_signal_source_oos
from src.paper.limit_signal_source_ranking import generate_limit_signal_source_ranking_report, rank_limit_signal_source_variants
from src.paper.limit_signal_source_store import save_limit_signal_source_variant_run
from src.paper.limit_signal_source_variants import build_limit_signal_source_variants
from src.risk.risk_store import load_latest_risk_snapshots
from src.scanners.hypothesis_ranking import _load_regimes, _signals_by_source
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


def _base_scenarios(include: bool, values: dict[str, float], base_key: str) -> dict[str, float]:
    return values if include else {base_key: values[base_key]}


def run(
    start: str | None = None,
    end: str | None = None,
    sources: list[str] | None = None,
    train_months: int = 1,
    test_months: int = 1,
    include_cost_scenarios: bool = False,
    include_slippage_scenarios: bool = False,
    include_regimes: bool = False,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    sources = [s.lower() for s in (sources or ["quant", "technical", "integrated"])]
    variants = build_limit_signal_source_variants()
    signals = _signals_by_source(db, sources, start, end)
    tickers = sorted({ticker for df in signals.values() if df is not None and not df.empty for ticker in df["ticker"].dropna().astype(str).str.upper().tolist()})
    prices = _load_price_history(db, tickers or None, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    regimes = _load_regimes(db, start, end) if include_regimes else pd.DataFrame()
    oos = run_limit_signal_source_oos(
        variants,
        signals,
        prices,
        risk_df=risk,
        regimes_df=regimes,
        cost_scenarios=_base_scenarios(include_cost_scenarios, {"LOW_COST": 5, "BASE_COST": 10, "HIGH_COST": 20, "STRESS_COST": 40}, "BASE_COST"),
        slippage_scenarios=_base_scenarios(include_slippage_scenarios, {"LOW_SLIPPAGE": 2, "BASE_SLIPPAGE": 5, "HIGH_SLIPPAGE": 20}, "BASE_SLIPPAGE"),
        train_months=train_months,
        test_months=test_months,
    )
    ranked = rank_limit_signal_source_variants(oos)
    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_limit_signal_source_variant_run(
            db,
            ranked,
            oos,
            start_date=start,
            end_date=end,
            metadata={"sources": sources, "include_cost_scenarios": include_cost_scenarios, "include_slippage_scenarios": include_slippage_scenarios, "include_regimes": include_regimes, "dry_run": dry_run, "nao_recomendacao": True},
        )
    csv_paths = {}
    if csv:
        csv_paths = {"variants": _write_csv(variants, "limit_signal_source_variants"), "ranking": _write_csv(ranked, "limit_signal_source_ranking")}
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "variants_count": int(len(variants)),
        "oos_rows": int(len(oos)),
        "ranked_rows": int(len(ranked)),
        "best_variant_id": str(ranked.iloc[0]["variant_id"]) if not ranked.empty else "",
        "best_score": float(ranked.iloc[0]["variant_robustness_score"]) if not ranked.empty else 0.0,
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "variants_df": variants,
        "oos_df": oos,
        "ranked_df": ranked,
        "report": generate_limit_signal_source_ranking_report(ranked),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calibração LIMIT_SIGNAL_SOURCE. Simulação e não recomendação.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--sources", nargs="+", default=["quant", "technical", "integrated"])
    parser.add_argument("--train-months", type=int, default=1)
    parser.add_argument("--test-months", type=int, default=1)
    parser.add_argument("--include-cost-scenarios", action="store_true")
    parser.add_argument("--include-slippage-scenarios", action="store_true")
    parser.add_argument("--include-regimes", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print("LIMIT_SIGNAL_SOURCE CALIBRATION")
    print(f"Status: {result['status']}")
    print(f"Variações testadas: {result['variants_count']}")
    print(f"Linhas OOS: {result['oos_rows']}")
    print(f"Melhor variação paramétrica em estudo: {result['best_variant_id']} ({result['best_score']:.2f})")
    if result["saved_run_id"]:
        print(f"Run salvo: {result['saved_run_id']}")
    if result["csv_paths"]:
        print(f"CSVs: {result['csv_paths']}")
    print("Não recomendação: nenhuma variação é aplicada automaticamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
