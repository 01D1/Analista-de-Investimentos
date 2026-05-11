"""CLI para review de governança quantitativa."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

from src.quant.governance import evaluate_candidate_strategy, generate_governance_report
from src.quant.governance_store import save_governance_review
from src.utils import load_config, project_path


SOURCE_TABLES = {
    "filter_walk_forward": "filter_walk_forward_runs",
    "walk_forward": "walk_forward_runs",
    "historical_backtest": "historical_backtest_runs",
    "threshold_optimization": "threshold_optimization_runs",
}


def _read_source(db_path: Path, source: str, run_id: int | None = None, latest: bool = False) -> pd.DataFrame:
    table = SOURCE_TABLES.get(source)
    if not table or not db_path.exists():
        return pd.DataFrame()
    where = ""
    params: list[int] = []
    if run_id is not None:
        where = "WHERE id = ?"
        params.append(int(run_id))
    order = "ORDER BY id DESC LIMIT 1" if latest or run_id is None else ""
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if exists is None:
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM {table} {where} {order}", con, params=params)
    except Exception:
        return pd.DataFrame()


def _metrics_from_source(source: str, row: pd.Series) -> dict:
    if source == "filter_walk_forward":
        return {
            "total_signals": row.get("avg_test_signals", 0),
            "windows_count": row.get("windows_count", 0),
            "positive_windows_pct": row.get("positive_windows_pct", 0),
            "mean_test_net_return": row.get("mean_test_net_return", 0),
            "mean_hit_rate": row.get("mean_test_hit_rate", 0),
            "avg_top_3_concentration_pct": row.get("avg_top_3_concentration_pct", 0),
            "overfitting_alert": bool(row.get("overfitting_alert", 0)),
            "robustness_class": row.get("robustness_class"),
        }
    if source == "walk_forward":
        return {
            "total_signals": row.get("windows_count", 0),
            "windows_count": row.get("windows_count", 0),
            "positive_windows_pct": row.get("positive_windows_pct", 0),
            "mean_test_net_return": row.get("mean_test_return", 0),
            "mean_hit_rate": row.get("mean_test_hit_rate", 0),
            "overfitting_alert": bool(row.get("overfitting_alert", 0)),
        }
    if source == "historical_backtest":
        return {
            "total_signals": row.get("signals_count", 0),
            "windows_count": 0,
            "positive_windows_pct": 0,
            "mean_test_net_return": row.get("mean_net_return_5d", row.get("mean_return_5d", 0)),
            "mean_hit_rate": row.get("net_hit_rate_5d", row.get("hit_rate_5d", 0)),
            "sample_warning": True,
        }
    if source == "threshold_optimization":
        return {
            "total_signals": row.get("best_samples", 0),
            "windows_count": 0,
            "positive_windows_pct": 0,
            "mean_test_net_return": row.get("best_mean_net_return", 0),
            "mean_hit_rate": row.get("best_hit_rate", 0),
            "sample_warning": True,
            "overfitting_alert": bool(row.get("overfitting_warning")),
        }
    return {}


def _apply_rule_overrides(metrics: dict, args: argparse.Namespace) -> tuple[dict, dict]:
    rules = {}
    if args.min_windows is not None:
        rules["min_windows"] = args.min_windows
    if args.min_signals is not None:
        rules["min_total_signals"] = args.min_signals
    if args.min_positive_windows_pct is not None:
        rules["min_positive_windows_pct"] = args.min_positive_windows_pct
    if args.max_concentration_pct is not None:
        rules["max_top_3_concentration_pct"] = args.max_concentration_pct
    return metrics, rules


def run(
    *,
    source: str,
    run_id: int | None = None,
    latest: bool = False,
    save_db: bool = False,
    output_json: bool = False,
    min_windows: int | None = None,
    min_signals: int | None = None,
    min_positive_windows_pct: float | None = None,
    max_concentration_pct: float | None = None,
) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    data = _read_source(db_path, source, run_id=run_id, latest=latest)
    if data.empty:
        message = f"Sem dados para source={source}. Rode a análise correspondente com --save-db."
        print(message)
        return {"message": message, "review": {}}
    row = data.iloc[0]
    metrics = _metrics_from_source(source, row)
    args = argparse.Namespace(
        min_windows=min_windows,
        min_signals=min_signals,
        min_positive_windows_pct=min_positive_windows_pct,
        max_concentration_pct=max_concentration_pct,
    )
    metrics, rules = _apply_rule_overrides(metrics, args)
    review = evaluate_candidate_strategy(metrics, rules=rules)
    review.update(
        {
            "source_type": source,
            "source_run_id": int(row.get("id")) if pd.notna(row.get("id")) else run_id,
            "candidate_name": f"{source}_run_{int(row.get('id')) if pd.notna(row.get('id')) else run_id}",
            "metadata": {"source_row": row.to_dict(), "rules": rules},
        }
    )
    report = generate_governance_report(review)
    review["summary_text"] = review.get("summary_text") or report

    if output_json:
        print(json.dumps(review, ensure_ascii=False, indent=2, default=str))
    else:
        print("\nGOVERNANCE REVIEW — " + source.replace("_", " ").upper())
        print(f"Status: {review['governance_status']}")
        print(f"Aprovado: {'SIM' if review['approved'] else 'NÃO'}")
        print(f"Risco: {review['risk_level']}")
        print(f"Confiança: {review['confidence_level']}")
        print("\nMotivos favoráveis:")
        for item in review.get("reasons_for", []):
            print(f"- {item}")
        print("\nMotivos contra:")
        for item in review.get("reasons_against", []):
            print(f"- {item}")
        print("\nAções necessárias:")
        for item in review.get("required_actions", []):
            print(f"- {item}")
        print("\n" + report)

    review_id = None
    if save_db:
        review_id = save_governance_review(db_path, review)
        print(f"\nGovernance review salvo no banco. review_id={review_id}")
    return {"review": review, "review_id": review_id, "source": data}


def main() -> None:
    parser = argparse.ArgumentParser(description="Review de governança quantitativa.")
    parser.add_argument("--source", required=True, choices=sorted(SOURCE_TABLES), help="Fonte do candidato.")
    parser.add_argument("--run-id", type=int, default=None, help="Run específico da fonte.")
    parser.add_argument("--latest", action="store_true", help="Usa o último run da fonte.")
    parser.add_argument("--save-db", action="store_true", help="Salva review em governance_reviews.")
    parser.add_argument("--json", action="store_true", help="Imprime review em JSON.")
    parser.add_argument("--min-windows", type=int, default=None, help="Mínimo de janelas.")
    parser.add_argument("--min-signals", type=int, default=None, help="Mínimo de sinais.")
    parser.add_argument("--min-positive-windows-pct", type=float, default=None, help="Mínimo de janelas positivas.")
    parser.add_argument("--max-concentration-pct", type=float, default=None, help="Máximo de concentração top 3.")
    args = parser.parse_args()
    run(
        source=args.source,
        run_id=args.run_id,
        latest=args.latest,
        save_db=args.save_db,
        output_json=args.json,
        min_windows=args.min_windows,
        min_signals=args.min_signals,
        min_positive_windows_pct=args.min_positive_windows_pct,
        max_concentration_pct=args.max_concentration_pct,
    )


if __name__ == "__main__":
    main()
