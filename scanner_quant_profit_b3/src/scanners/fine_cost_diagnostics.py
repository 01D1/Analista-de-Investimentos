"""CLI de diagnostico fino de custos do paper trading."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.paper.exit_rule_cost_diagnostics import analyze_exit_rule_costs
from src.paper.fine_cost_diagnostics_store import save_fine_cost_diagnostics
from src.paper.order_reason_normalizer import normalize_orders_reasons
from src.paper.paper_store import load_paper_exit_events, load_paper_orders, load_paper_positions, load_paper_rebalance_events
from src.paper.position_cost_lifecycle import link_orders_to_position_lifecycle, summarize_lifecycle_costs
from src.paper.rebalance_cost_diagnostics import analyze_rebalance_costs, suggest_rebalance_diagnostics
from src.paper.unknown_cost_diagnostics import analyze_unknown_costs
from src.reports.fine_cost_diagnostics_report import save_fine_cost_diagnostics_markdown
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


def _rebalance_summary_to_df(result: dict) -> pd.DataFrame:
    summary = result.get("summary", {}) if result else {}
    by_ticker = result.get("rebalance_cost_by_ticker", pd.DataFrame()) if result else pd.DataFrame()
    if by_ticker is None or by_ticker.empty:
        return pd.DataFrame([{"ticker": "ALL", **summary}]) if summary else pd.DataFrame()
    out = by_ticker.copy()
    out["rebalance_cost_class"] = summary.get("rebalance_cost_class")
    out["metadata_json"] = summary.get("metadata_json", "{}")
    return out


def run(
    paper_run_id: int,
    save_db: bool = False,
    csv: bool = False,
    include_lifecycle: bool = True,
    include_rebalance: bool = True,
    include_exit_rules: bool = True,
    include_unknown: bool = True,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    orders = load_paper_orders(db, run_id=paper_run_id)
    positions = load_paper_positions(db, run_id=paper_run_id)
    exit_events = load_paper_exit_events(db, run_id=paper_run_id)
    rebalance_events = load_paper_rebalance_events(db, run_id=paper_run_id)

    order_reasons = normalize_orders_reasons(orders)
    lifecycle = link_orders_to_position_lifecycle(order_reasons, positions) if include_lifecycle else pd.DataFrame()
    lifecycle_summary = summarize_lifecycle_costs(lifecycle)
    rebalance_result = analyze_rebalance_costs(order_reasons, rebalance_events) if include_rebalance else {"summary": {}, "rebalance_cost_by_ticker": pd.DataFrame()}
    rebalance_df = _rebalance_summary_to_df(rebalance_result)
    exit_rules = analyze_exit_rule_costs(order_reasons, exit_events) if include_exit_rules else pd.DataFrame()
    unknown = analyze_unknown_costs(order_reasons) if include_unknown else {"summary": {}, "unknown_by_ticker": pd.DataFrame(), "unknown_by_date": pd.DataFrame(), "unknown_by_side": pd.DataFrame()}
    metadata_fixes = unknown.get("summary", {}).get("required_metadata_fixes", [])
    rebalance_suggestions = suggest_rebalance_diagnostics(rebalance_result.get("summary", {}))

    saved_run_id = None
    if save_db:
        saved_run_id = save_fine_cost_diagnostics(
            db,
            paper_run_id,
            order_reasons_df=order_reasons,
            lifecycle_df=lifecycle,
            rebalance_df=rebalance_df,
            exit_rule_df=exit_rules,
            unknown_summary=unknown.get("summary", {}),
        )

    csv_paths = {}
    if csv:
        csv_paths = {
            "order_reasons": _write_csv(order_reasons, "fine_cost_order_reasons"),
            "lifecycle": _write_csv(lifecycle, "fine_cost_lifecycle"),
            "rebalance": _write_csv(rebalance_df, "fine_cost_rebalance"),
            "exit_rules": _write_csv(exit_rules, "fine_cost_exit_rules"),
            "unknown": _write_csv(pd.DataFrame([unknown.get("summary", {})]), "fine_cost_unknown"),
        }

    report_path = ""
    if csv or save_db:
        report_path = str(
            save_fine_cost_diagnostics_markdown(
                _reports_dir() / f"fine_cost_diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                {
                    "order_reasons": order_reasons,
                    "lifecycle": lifecycle,
                    "lifecycle_summary": lifecycle_summary,
                    "rebalance": rebalance_result,
                    "exit_rules": exit_rules,
                    "unknown": unknown,
                    "metadata_fixes": metadata_fixes,
                    "rebalance_suggestions": rebalance_suggestions,
                },
            )
        )

    return {
        "status": "SUCCESS",
        "paper_run_id": paper_run_id,
        "saved_run_id": saved_run_id,
        "order_reasons": order_reasons,
        "lifecycle": lifecycle,
        "lifecycle_summary": lifecycle_summary,
        "rebalance": rebalance_result,
        "exit_rules": exit_rules,
        "unknown": unknown,
        "metadata_fixes": metadata_fixes,
        "rebalance_suggestions": rebalance_suggestions,
        "csv_paths": csv_paths,
        "report_path": report_path,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnostico fino de custos. Simulação, não recomendação.")
    parser.add_argument("--paper-run-id", type=int, required=True)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--include-lifecycle", action="store_true", default=True)
    parser.add_argument("--include-rebalance", action="store_true", default=True)
    parser.add_argument("--include-exit-rules", action="store_true", default=True)
    parser.add_argument("--include-unknown", action="store_true", default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    result = run(**vars(build_parser().parse_args(argv)))
    life = result["lifecycle_summary"]
    reb = result["rebalance"].get("summary", {})
    unk = result["unknown"].get("summary", {})
    print("FINE COST DIAGNOSTICS")
    print(f"Status: {result['status']}")
    print(f"Paper run: {result['paper_run_id']}")
    print(f"Entrada %: {life.get('entry_cost_pct', 0):.4f}")
    print(f"Saída %: {life.get('exit_cost_pct', 0):.4f}")
    print(f"Rebalance %: {life.get('rebalance_cost_pct', 0):.4f}")
    print(f"Classe rebalance: {reb.get('rebalance_cost_class', 'REBALANCE_DATA_INSUFFICIENT')}")
    print(f"Ordens/metadados UNKNOWN: {unk.get('unknown_orders_count', 0)}")
    if result["saved_run_id"]:
        print(f"Diagnóstico salvo para paper_run_id: {result['saved_run_id']}")
    if result["report_path"]:
        print(f"Relatório: {result['report_path']}")
    print("Não recomendação: diagnóstico simulado, sem ordens reais e sem alteração de score/ranking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
