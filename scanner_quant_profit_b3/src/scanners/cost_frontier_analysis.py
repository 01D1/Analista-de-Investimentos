"""CLI da fronteira custo-retorno-drawdown."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.cost_efficiency_frontier import calculate_cost_efficiency_frontier
from src.paper.cost_frontier_governance import evaluate_cost_frontier_candidate
from src.paper.cost_frontier_store import save_cost_frontier_run
from src.paper.cost_reduction_store import load_cost_reduction_results
from src.paper.cost_return_tradeoff import calculate_tradeoff_metrics
from src.paper.cost_tradeoff_score import calculate_cost_tradeoff_score
from src.reports.cost_frontier_report import save_cost_frontier_report
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


def analyze(cost_reduction_results: pd.DataFrame) -> pd.DataFrame:
    tradeoff = calculate_tradeoff_metrics(cost_reduction_results)
    frontier = calculate_cost_efficiency_frontier(tradeoff)
    if frontier.empty:
        return frontier
    score_rows = frontier.apply(lambda row: calculate_cost_tradeoff_score(row), axis=1, result_type="expand")
    out = pd.concat([frontier.reset_index(drop=True), score_rows.reset_index(drop=True)], axis=1)
    out["governance_status"] = out.apply(evaluate_cost_frontier_candidate, axis=1)
    out = out.sort_values(["tradeoff_score", "efficiency_score"], ascending=False).reset_index(drop=True)
    return out


def run(cost_reduction_run_id: int, save_db: bool = False, csv: bool = False, dry_run: bool = False, db_path: str | Path | None = None) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    source = load_cost_reduction_results(db, run_id=cost_reduction_run_id)
    results = analyze(source)
    saved_run_id = None
    if save_db and not dry_run:
        saved_run_id = save_cost_frontier_run(db, cost_reduction_run_id, results, metadata={"dry_run": dry_run, "nao_recomendacao": True})
    csv_path = _write_csv(results, "cost_frontier_results") if csv else ""
    report_path = ""
    if csv or save_db:
        report_path = str(save_cost_frontier_report(_reports_dir() / f"cost_frontier_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", cost_reduction_run_id, results))
    best = results.iloc[0].to_dict() if not results.empty else {}
    return {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "cost_reduction_run_id": cost_reduction_run_id,
        "variants_count": int(len(results)),
        "efficient_count": int(results.get("is_efficient", pd.Series(dtype=bool)).astype(bool).sum()) if not results.empty else 0,
        "best_variant_id": best.get("variant_id"),
        "best_tradeoff_score": best.get("tradeoff_score"),
        "saved_run_id": saved_run_id,
        "csv_path": csv_path,
        "report_path": report_path,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fronteira custo-retorno-drawdown. Não recomendação.")
    parser.add_argument("--cost-reduction-run-id", type=int, required=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    print("COST FRONTIER ANALYSIS")
    print(f"Status: {result['status']}")
    print(f"Cost reduction run: {result['cost_reduction_run_id']}")
    print(f"Variantes analisadas: {result['variants_count']}")
    print(f"Variantes eficientes: {result['efficient_count']}")
    print(f"Melhor trade-off: {result.get('best_variant_id') or '-'}")
    print(f"Score: {result.get('best_tradeoff_score') or 0}")
    if result.get("saved_run_id"):
        print(f"Run salvo: {result['saved_run_id']}")
    if result.get("csv_path"):
        print(f"CSV: {result['csv_path']}")
    if result.get("report_path"):
        print(f"Relatório: {result['report_path']}")
    print("Não recomendação: análise de fronteira, sem ordens reais e sem aplicação automática.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
