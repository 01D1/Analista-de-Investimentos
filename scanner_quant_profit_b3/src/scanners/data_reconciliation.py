"""CLI geral de reconciliacao de fontes."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.data_quality.b3_reconciliation import compare_b3_raw_vs_sqlite, summarize_b3_raw_files, summarize_b3_sqlite
from src.data_quality.file_manifest import build_file_manifest, compare_file_manifest
from src.data_quality.file_manifest_store import load_latest_file_manifest, save_file_manifest_run
from src.data_quality.options_reconciliation import compare_options_expectation_vs_available, summarize_options_sources
from src.data_quality.profit_reconciliation import check_profit_freshness, suggest_profit_actions
from src.data_quality.reconciliation_alerts import build_alerts_from_reconciliation
from src.data_quality.reconciliation_store import save_reconciliation_run
from src.data_quality.ri_reconciliation import detect_missing_ri_urls, suggest_ri_url_template
from src.notifications.alert_store import save_alerts
from src.utils import load_config, project_path


RECON_COLUMNS = ["source_domain", "issue_type", "severity", "status", "description", "suggested_command", "executed", "execution_status", "metadata_json"]


def _write_csv(df: pd.DataFrame, prefix: str) -> Path | None:
    if df.empty:
        return None
    out = project_path("data/reports")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def _row(domain: str, issue: str, severity: str, description: str, command: str = "", metadata: dict | None = None, status: str = "OPEN") -> dict:
    return {
        "source_domain": domain,
        "issue_type": issue,
        "severity": severity,
        "status": status,
        "description": description,
        "suggested_command": command,
        "executed": False,
        "execution_status": "NOT_EXECUTED",
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, default=str),
    }


def _profit_results() -> pd.DataFrame:
    audit = check_profit_freshness()
    if audit["status"] == "OK":
        rows = [_row("PROFIT_RTD", "OK", "INFO", audit["message"], "", audit, status="OK")]
    else:
        rows = [
            _row(
                "PROFIT_RTD",
                "PROFIT_RTD_STALE" if audit["status"] == "STALE" else "PROFIT_RTD_ERROR",
                "WARNING",
                audit["message"],
                "python -m src.scanners.realtime_profit_scanner --once --save-db",
                {"audit": audit, "actions": suggest_profit_actions(audit)},
            )
        ]
    return pd.DataFrame(rows, columns=RECON_COLUMNS)


def _ri_results() -> pd.DataFrame:
    missing = detect_missing_ri_urls()
    if missing.empty:
        return pd.DataFrame([_row("RI", "INSUFFICIENT_DATA", "WARNING", "Nenhum cadastro de empresa encontrado para reconciliar RI.", "", {}, "OPEN")], columns=RECON_COLUMNS)
    rows = []
    for _, row in missing[~missing["has_ri_url"].astype(bool)].iterrows():
        rows.append(
            _row(
                "RI",
                "RI_URL_MISSING",
                "INFO",
                f"{row.get('ticker')} sem URL de RI configurada.",
                "",
                {"template": suggest_ri_url_template(row.get("ticker", ""), row.get("company_name", "")), "row": row.to_dict()},
            )
        )
    if not rows:
        rows.append(_row("RI", "OK", "INFO", "Todas as empresas mapeadas possuem URL de RI.", "", {"rows": len(missing)}, status="OK"))
    return pd.DataFrame(rows, columns=RECON_COLUMNS)


def run(
    *,
    sources: list[str] | None = None,
    save_db: bool = False,
    csv: bool = False,
    suggest_fixes: bool = False,
    execute_fixes: bool = False,
    confirm: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg.get("database_path", "data/database/scanner_quant.db"))
    selected = sources or ["b3", "options", "profit", "ri"]
    if "all" in selected:
        selected = ["b3", "options", "profit", "ri"]
    frames = []
    if "b3" in selected:
        frames.append(compare_b3_raw_vs_sqlite(summarize_b3_raw_files(cfg.get("b3", {}).get("raw_dir", "data/raw")), summarize_b3_sqlite(db))[RECON_COLUMNS])
    if "options" in selected:
        underlyings = cfg.get("ativos_base", [])
        frames.append(compare_options_expectation_vs_available(underlyings, summarize_options_sources(db))[RECON_COLUMNS])
    if "profit" in selected:
        frames.append(_profit_results())
    if "ri" in selected:
        frames.append(_ri_results())
    results = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=RECON_COLUMNS)
    if execute_fixes and not confirm:
        print("Execucao bloqueada: use --execute-fixes --confirm. Nenhuma correcao foi executada.")
    # A execucao real fica restrita ao CLI especifico de B3 nesta fase.
    summary = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "reconciliation_type": ",".join(selected),
        "status": "OK" if results["issue_type"].eq("OK").all() else "WARNING",
        "issues_count": int((results["issue_type"] != "OK").sum()),
        "fixes_suggested_count": int(results["suggested_command"].astype(str).str.len().gt(0).sum()),
        "fixes_executed_count": 0,
    }
    run_id = save_reconciliation_run(db, summary, results) if save_db else 0
    manifest_run_id = 0
    if save_db:
        manifest_dirs = [
            "data/raw",
            "data/processed",
            "../12_PYTHON/pipeline banco completo/data/qualitative",
            "../12_PYTHON/news_hunter/dados",
        ]
        manifest = build_file_manifest(manifest_dirs, patterns=["**/*.ZIP", "**/*.zip", "**/*.TXT", "**/*.txt", "**/*.json", "**/*.xlsx", "**/*.csv"])
        previous = load_latest_file_manifest(db)
        manifest_run_id = save_file_manifest_run(db, manifest, compare_file_manifest(previous, manifest))
    alerts_saved = save_alerts(db, build_alerts_from_reconciliation(results)) if save_db else 0
    csv_path = _write_csv(results, "data_reconciliation_results") if csv else None
    print("\nDATA RECONCILIATION")
    for _, row in results.iterrows():
        print(f"{row.get('severity')}: {row.get('source_domain')} — {row.get('issue_type')} — {row.get('description')}")
        if suggest_fixes and row.get("suggested_command"):
            print(f"  Sugestao: {row.get('suggested_command')}")
    print(f"Issues: {summary['issues_count']} | Fixes sugeridos: {summary['fixes_suggested_count']}")
    if csv_path:
        print(f"CSV: {csv_path}")
    if run_id:
        print(f"Run salvo: {run_id}; manifesto: {manifest_run_id}; alertas: {alerts_saved}")
    return {"results": results, "summary": summary, "run_id": run_id, "manifest_run_id": manifest_run_id, "alerts_saved": alerts_saved, "csv_path": csv_path}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconcilia fontes de dados em modo dry-run por padrao.")
    parser.add_argument("--sources", nargs="*", default=["b3", "options", "profit", "ri"], choices=["b3", "options", "profit", "ri", "all"])
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--suggest-fixes", action="store_true")
    parser.add_argument("--execute-fixes", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run(sources=args.sources, save_db=args.save_db, csv=args.csv, suggest_fixes=args.suggest_fixes, execute_fixes=args.execute_fixes, confirm=args.confirm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
