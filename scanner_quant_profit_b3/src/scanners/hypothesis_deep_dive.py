"""CLI de deep dive OOS de hipoteses em estudo."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.hypothesis_asset_decomposition import decompose_hypothesis_by_asset
from src.paper.hypothesis_block_explanations import explain_hypothesis_blockage
from src.paper.hypothesis_deep_dive_selection import select_top_hypotheses_for_deep_dive
from src.paper.hypothesis_deep_governance import evaluate_deep_hypothesis_governance
from src.paper.hypothesis_deep_oos import run_deep_oos_validation
from src.paper.hypothesis_deep_store import save_hypothesis_deep_oos_run
from src.paper.hypothesis_ranking_store import load_hypothesis_ranking_results
from src.paper.hypothesis_signal_source_decomposition import decompose_hypothesis_by_signal_source
from src.paper.hypothesis_universe import build_default_hypothesis_universe
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


def _load_events(db_path: Path, start: str | None, end: str | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as con:
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_events'").fetchone() is None:
                return pd.DataFrame()
            df = pd.read_sql_query("SELECT * FROM market_events", con)
    except sqlite3.Error:
        return pd.DataFrame()
    date_col = "event_date" if "event_date" in df.columns else "trade_date" if "trade_date" in df.columns else ""
    if date_col:
        df[date_col] = df[date_col].astype(str)
        if start:
            df = df[df[date_col] >= str(start)]
        if end:
            df = df[df[date_col] <= str(end)]
    return df


def _scenario_dict(enabled: bool, defaults: dict[str, float]) -> dict[str, float]:
    if enabled:
        return defaults
    base = [k for k in defaults if "BASE" in k]
    return {base[0]: defaults[base[0]]} if base else defaults


def _summary_for_governance(hypothesis_id: str, deep: pd.DataFrame, reasons: pd.DataFrame, asset_decomp: pd.DataFrame) -> dict:
    hyp_rows = deep[deep["hypothesis_id"].astype(str).eq(str(hypothesis_id))].copy()
    base_rows = hyp_rows[hyp_rows.get("ticker", pd.Series(dtype=str)).astype(str).eq("TODOS")]
    metric_rows = base_rows if not base_rows.empty else hyp_rows
    useful = metric_rows[metric_rows.get("data_coverage_status", "").astype(str).eq("COVERAGE_USEFUL")]
    reason_row = reasons[reasons["hypothesis_id"].astype(str).eq(str(hypothesis_id))].head(1)
    asset_rows = asset_decomp[asset_decomp["hypothesis_id"].astype(str).eq(str(hypothesis_id))] if asset_decomp is not None and not asset_decomp.empty else pd.DataFrame()
    return {
        "hypothesis_id": hypothesis_id,
        "positive_improvement_pct": float(pd.to_numeric(metric_rows.get("positive_improvement_pct"), errors="coerce").mean()) if not metric_rows.empty else 0.0,
        "mean_return_delta": float(pd.to_numeric(metric_rows.get("mean_return_delta"), errors="coerce").mean()) if not metric_rows.empty else 0.0,
        "mean_drawdown_delta": float(pd.to_numeric(metric_rows.get("mean_drawdown_delta"), errors="coerce").mean()) if not metric_rows.empty else 0.0,
        "mean_fragility_delta": float(pd.to_numeric(metric_rows.get("mean_fragility_delta"), errors="coerce").mean()) if not metric_rows.empty else 0.0,
        "useful_sources_count": int(useful["signal_source"].nunique()) if not useful.empty and "signal_source" in useful.columns else 0,
        "useful_regimes_count": int(useful.loc[useful["regime"].astype(str).ne("SEM_REGIME"), "regime"].nunique()) if not useful.empty and "regime" in useful.columns else 0,
        "asset_concentration_pct": float(pd.to_numeric(asset_rows.get("contribution_to_blockage"), errors="coerce").max()) if not asset_rows.empty else 0.0,
        "cost_sensitivity_flag": bool(metric_rows.get("cost_sensitivity_flag", pd.Series(dtype=bool)).astype(bool).any()) if not metric_rows.empty else False,
        "slippage_sensitivity_flag": bool(metric_rows.get("slippage_sensitivity_flag", pd.Series(dtype=bool)).astype(bool).any()) if not metric_rows.empty else False,
        "overfitting_flag": bool(metric_rows.get("overfitting_flag", pd.Series(dtype=bool)).astype(bool).any()) if not metric_rows.empty else False,
        "primary_block_reason": str(reason_row.iloc[0]["primary_block_reason"]) if not reason_row.empty else "",
    }


def _merge_selection_with_universe(selection: pd.DataFrame) -> pd.DataFrame:
    universe = build_default_hypothesis_universe()
    if selection.empty:
        return pd.DataFrame()
    merged = selection.merge(universe, on="hypothesis_id", how="left", suffixes=("_selected", ""))
    if "hypothesis_type" not in merged.columns:
        merged["hypothesis_type"] = merged.get("hypothesis_type_selected", merged["hypothesis_id"])
    merged["hypothesis_type"] = merged["hypothesis_type"].fillna(merged.get("hypothesis_type_selected", merged["hypothesis_id"]))
    merged["parameters_json"] = (merged["parameters_json"] if "parameters_json" in merged.columns else pd.Series("{}", index=merged.index)).fillna("{}")
    merged["can_simulate"] = (merged["can_simulate"] if "can_simulate" in merged.columns else pd.Series(True, index=merged.index)).fillna(True)
    return merged


def run(
    ranking_run_id: int | None = None,
    hypotheses: list[str] | None = None,
    top_n: int = 3,
    start: str | None = None,
    end: str | None = None,
    include_cost_scenarios: bool = True,
    include_slippage_scenarios: bool = True,
    include_regimes: bool = True,
    include_assets: bool = True,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    ranking = load_hypothesis_ranking_results(db, run_id=ranking_run_id) if ranking_run_id else load_hypothesis_ranking_results(db)
    selection = select_top_hypotheses_for_deep_dive(ranking, top_n=top_n, manual_hypotheses=hypotheses)
    selected_hypotheses = _merge_selection_with_universe(selection)

    sources = ["quant", "technical", "integrated"]
    signals = _signals_by_source(db, sources, start, end)
    tickers = sorted({ticker for df in signals.values() if df is not None and not df.empty for ticker in df["ticker"].dropna().astype(str).str.upper().tolist()})
    prices = _load_price_history(db, tickers or None, start, end)
    risk = load_latest_risk_snapshots(db, tickers) if tickers else pd.DataFrame()
    regimes = _load_regimes(db, start, end) if include_regimes else pd.DataFrame()
    events = _load_events(db, start, end)

    cost_scenarios = _scenario_dict(include_cost_scenarios, {"LOW_COST": 5, "BASE_COST": 10, "HIGH_COST": 20, "STRESS_COST": 40})
    slippage_scenarios = _scenario_dict(include_slippage_scenarios, {"LOW_SLIPPAGE": 2, "BASE_SLIPPAGE": 5, "HIGH_SLIPPAGE": 20})

    deep_frames = []
    for _, hyp in selected_hypotheses.iterrows():
        if not bool(hyp.get("can_simulate", True)):
            continue
        deep_frames.append(
            run_deep_oos_validation(
                hyp.to_dict(),
                signals,
                prices,
                risk_df=risk,
                regimes_df=regimes,
                events_df=events,
                cost_scenarios=cost_scenarios,
                slippage_scenarios=slippage_scenarios,
                include_assets=include_assets,
            )
        )
    deep = pd.concat(deep_frames, ignore_index=True) if deep_frames else pd.DataFrame()
    asset_decomp = decompose_hypothesis_by_asset(deep)
    source_decomp = decompose_hypothesis_by_signal_source(deep)
    block_reasons = explain_hypothesis_blockage(deep)

    if not deep.empty:
        governance_map = {}
        for hyp_id in deep["hypothesis_id"].dropna().astype(str).unique().tolist():
            governance_map[hyp_id] = evaluate_deep_hypothesis_governance(_summary_for_governance(hyp_id, deep, block_reasons, asset_decomp))
        deep["governance_status"] = deep["hypothesis_id"].astype(str).map(governance_map).fillna("HYPOTHESIS_DEEP_MORE_TESTING_REQUIRED")
        for hyp_id, status in governance_map.items():
            mask = block_reasons["hypothesis_id"].astype(str).eq(str(hyp_id)) if not block_reasons.empty else pd.Series(dtype=bool)
            if not block_reasons.empty and mask.any():
                meta = {"governance_status": status, "nao_recomendacao": True}
                block_reasons.loc[mask, "metadata_json"] = block_reasons.loc[mask, "metadata_json"].apply(lambda raw: json.dumps({**(json.loads(raw or "{}") if isinstance(raw, str) else {}), **meta}, ensure_ascii=False, default=str))
    else:
        deep["governance_status"] = pd.Series(dtype=str)

    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_hypothesis_deep_oos_run(
            db,
            deep,
            block_reasons,
            start_date=start,
            end_date=end,
            metadata={
                "ranking_run_id": ranking_run_id,
                "selection": selection.to_dict(orient="records"),
                "include_cost_scenarios": include_cost_scenarios,
                "include_slippage_scenarios": include_slippage_scenarios,
                "include_regimes": include_regimes,
                "include_assets": include_assets,
                "dry_run": dry_run,
                "nao_recomendacao": True,
            },
        )

    csv_paths = {}
    if csv:
        csv_paths = {
            "results": _write_csv(deep, "hypothesis_deep_oos_results"),
            "block_reasons": _write_csv(block_reasons, "hypothesis_block_reasons"),
            "asset_decomposition": _write_csv(asset_decomp, "hypothesis_asset_decomposition"),
            "source_decomposition": _write_csv(source_decomp, "hypothesis_source_decomposition"),
        }

    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "selected_hypotheses": selection,
        "deep_rows": int(len(deep)),
        "block_reasons_rows": int(len(block_reasons)),
        "asset_decomposition_rows": int(len(asset_decomp)),
        "source_decomposition_rows": int(len(source_decomp)),
        "saved_run_id": saved_run_id,
        "csv_paths": csv_paths,
        "deep_oos_df": deep,
        "block_reasons_df": block_reasons,
        "asset_decomposition_df": asset_decomp,
        "source_decomposition_df": source_decomp,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deep dive OOS de hipoteses em estudo. Nao recomendacao.")
    parser.add_argument("--ranking-run-id", type=int)
    parser.add_argument("--hypotheses", nargs="+")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--include-cost-scenarios", action="store_true", default=True)
    parser.add_argument("--include-slippage-scenarios", action="store_true", default=True)
    parser.add_argument("--include-regimes", action="store_true", default=True)
    parser.add_argument("--include-assets", action="store_true", default=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(**vars(args))
    print("HYPOTHESIS DEEP DIVE")
    print(f"Status: {result['status']}")
    selected = result["selected_hypotheses"]
    print(f"Hipóteses em estudo: {', '.join(selected['hypothesis_id'].astype(str).tolist()) if not selected.empty else '-'}")
    print(f"Linhas OOS profundas: {result['deep_rows']}")
    print(f"Motivos de bloqueio: {result['block_reasons_rows']}")
    if result["saved_run_id"]:
        print(f"Run salvo: {result['saved_run_id']}")
    if result["csv_paths"]:
        print(f"CSVs: {result['csv_paths']}")
    print("Não recomendação: simulação, investigação e explicação; nenhuma hipótese é aplicada automaticamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
