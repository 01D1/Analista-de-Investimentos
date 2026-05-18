"""CLI de auditoria de fontes de dados e confiabilidade."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.b3_audit import audit_b3_cotahist
from src.data_quality.cvm_audit import audit_cvm_ipe
from src.data_quality.data_quality_alerts import build_alerts_from_data_source_audit
from src.data_quality.data_source_audit_store import save_data_source_audit_run, save_traceability_records
from src.data_quality.news_event_audit import audit_event_pipeline, audit_news_hunter
from src.data_quality.options_data_audit import audit_options_data
from src.data_quality.profit_rtd_audit import audit_profit_excel
from src.data_quality.ri_audit import audit_ri_sites, load_ri_urls
from src.data_quality.source_inventory import AUDIT_RESULT_COLUMNS, build_traceability_records, make_audit_row
from src.data_quality.source_reliability import calculate_source_reliability_score, generate_source_reliability_report
from src.data_quality.valuation_audit import audit_valuation_outputs
from src.notifications.alert_store import save_alerts
from src.utils import load_config, project_path


DEFAULT_SOURCES = ["profit", "b3", "cvm", "ri", "news", "events", "valuation", "options"]


def _write_csv(df: pd.DataFrame, prefix: str) -> Path | None:
    if df is None or df.empty:
        return None
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _run_ri(check_online: bool) -> dict:
    ri = audit_ri_sites(load_ri_urls(), check_online=check_online)
    configured = int(ri["url_configured"].fillna(False).astype(bool).sum()) if not ri.empty else 0
    ok = int(ri["status"].astype(str).str.upper().isin(["OK", "NOT_CHECKED"]).sum()) if not ri.empty else 0
    return make_audit_row(
        source_name="ri_sites",
        source_type="COMPANY_IR",
        primary_or_secondary="PRIMARY",
        expected_path_or_url="../12_PYTHON/pipeline banco completo/config/empresas.yaml",
        available=configured > 0,
        records_count=len(ri),
        tickers_count=configured,
        coverage_scope="company_ir_urls",
        status="OK" if ok and configured else "MISSING",
        message=f"{configured} URLs de RI configuradas; online={check_online}.",
        metadata={"ri_sites": ri.to_dict(orient="records")},
    )


def run(
    *,
    sources: list[str] | None = None,
    check_ri_online: bool = False,
    save_db: bool = False,
    csv: bool = False,
    verbose: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    started_at = datetime.now().isoformat(timespec="seconds")
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    selected = sources or DEFAULT_SOURCES
    rows: list[dict] = []
    if "profit" in selected:
        rows.append(audit_profit_excel())
    if "b3" in selected:
        b3_cfg = cfg.get("b3", {})
        rows.append(audit_b3_cotahist(b3_cfg.get("raw_dir", "data/raw"), b3_cfg.get("processed_dir", "data/processed"), db))
    if "cvm" in selected:
        rows.append(audit_cvm_ipe())
    if "ri" in selected:
        rows.append(_run_ri(check_ri_online))
    if "news" in selected:
        rows.append(audit_news_hunter())
    if "events" in selected:
        rows.append(audit_event_pipeline(db))
    if "valuation" in selected:
        rows.append(audit_valuation_outputs())
    if "options" in selected:
        rows.append(audit_options_data(db))

    audit_df = pd.DataFrame(rows, columns=AUDIT_RESULT_COLUMNS)
    reliability_df = calculate_source_reliability_score(audit_df)
    traceability_df = build_traceability_records(reliability_df)
    status_counts = reliability_df["status"].astype(str).str.upper().value_counts().to_dict() if not reliability_df.empty else {}
    overall_score = float(reliability_df["reliability_score"].mean()) if not reliability_df.empty else 0.0
    critical = int(sum(status_counts.get(s, 0) for s in ["ERROR", "MISSING"]))
    overall_status = "CRITICAL" if critical else ("WARNING" if status_counts.get("WARNING", 0) or status_counts.get("STALE", 0) else ("OK" if len(reliability_df) else "NO_DATA"))
    summary = {
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "status": overall_status,
        "sources_checked": len(reliability_df),
        "ok_count": int(status_counts.get("OK", 0)),
        "warning_count": int(status_counts.get("WARNING", 0) + status_counts.get("STALE", 0)),
        "error_count": int(status_counts.get("ERROR", 0)),
        "missing_count": int(status_counts.get("MISSING", 0)),
        "overall_reliability_score": round(overall_score, 2),
        "overall_status": overall_status,
    }
    run_id = save_data_source_audit_run(db, summary, reliability_df) if save_db else 0
    trace_saved = save_traceability_records(db, traceability_df) if save_db else 0
    alerts_saved = save_alerts(db, build_alerts_from_data_source_audit(reliability_df)) if save_db else 0
    csv_results = _write_csv(reliability_df, "data_source_audit_results") if csv else None
    csv_trace = _write_csv(traceability_df, "data_source_traceability") if csv else None

    print("\nDATA SOURCE AUDIT")
    for _, row in reliability_df.iterrows():
        print(f"{row.get('status')}: {row.get('source_name')} — score {row.get('reliability_score'):.1f} — {row.get('message')}")
        if verbose:
            print(f"  {row.get('expected_path_or_url')}")
    print(f"\nOverall status: {overall_status}")
    print(f"Confiabilidade geral: {overall_score:.1f}")
    if csv_results:
        print(f"CSV resultados: {csv_results}")
    if csv_trace:
        print(f"CSV rastreabilidade: {csv_trace}")
    if save_db:
        print(f"Run salvo: {run_id}; rastreabilidade: {trace_saved}; alertas: {alerts_saved}")
    if verbose:
        print(generate_source_reliability_report(reliability_df))

    return {"summary": summary, "results": reliability_df, "traceability": traceability_df, "run_id": run_id, "alerts_saved": alerts_saved, "csv_results": csv_results, "csv_traceability": csv_trace}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audita fontes de dados, cobertura e rastreabilidade.")
    parser.add_argument("--sources", nargs="*", choices=DEFAULT_SOURCES, default=None)
    parser.add_argument("--check-ri-online", action="store_true")
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run(sources=args.sources, check_ri_online=args.check_ri_online, save_db=args.save_db, csv=args.csv, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

