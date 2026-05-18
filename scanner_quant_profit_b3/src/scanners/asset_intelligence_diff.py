"""CLI para comparar snapshots integrados por ativo."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.integration.asset_intelligence_alerts import build_alerts_from_asset_diffs
from src.integration.asset_intelligence_diff import compare_latest_snapshots, detect_material_changes
from src.integration.asset_intelligence_diff_store import save_asset_intelligence_diffs
from src.integration.asset_intelligence_store import load_asset_intelligence_history
from src.notifications.alert_store import save_alerts
from src.utils import load_config, project_path


def _write_csv(df: pd.DataFrame) -> Path | None:
    if df.empty:
        return None
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"asset_intelligence_diffs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def run(
    latest: bool = True,
    tickers: list[str] | None = None,
    save_db: bool = False,
    csv: bool = False,
    material_only: bool = False,
    limit: int = 5000,
    db_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    snapshots = load_asset_intelligence_history(db, limit=limit)
    if tickers and not snapshots.empty:
        allowed = {str(t).upper() for t in tickers}
        snapshots = snapshots[snapshots["ticker"].astype(str).str.upper().isin(allowed)].copy()
    diffs = compare_latest_snapshots(snapshots) if latest else compare_latest_snapshots(snapshots)
    diffs = detect_material_changes(diffs)
    if material_only and not diffs.empty:
        diffs = diffs[diffs["material_change"].fillna(False).astype(bool)].copy()
    saved = save_asset_intelligence_diffs(db, diffs) if save_db else 0
    alerts_saved = 0
    if save_db and not diffs.empty:
        alerts_saved = save_alerts(db, build_alerts_from_asset_diffs(diffs))
    csv_path = _write_csv(diffs) if csv else None
    return {
        "snapshots_count": int(len(snapshots)),
        "diffs_count": int(len(diffs)),
        "material_changes": int(diffs["material_change"].fillna(False).astype(bool).sum()) if not diffs.empty else 0,
        "governance_changes": int(diffs["governance_changed"].fillna(False).astype(bool).sum()) if not diffs.empty else 0,
        "status_changes": int(diffs["status_changed"].fillna(False).astype(bool).sum()) if not diffs.empty else 0,
        "valuation_changes": int(diffs["valuation_changed"].fillna(False).astype(bool).sum()) if not diffs.empty else 0,
        "regime_changes": int(diffs["regime_changed"].fillna(False).astype(bool).sum()) if not diffs.empty else 0,
        "rows_saved": saved,
        "alerts_saved": alerts_saved,
        "csv_path": str(csv_path) if csv_path else "",
        "data": diffs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compara snapshots integrados por ativo.")
    parser.add_argument("--latest", action="store_true", default=True)
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--material-only", action="store_true")
    parser.add_argument("--limit", type=int, default=5000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(
        latest=args.latest,
        tickers=args.tickers,
        save_db=args.save_db,
        csv=args.csv,
        material_only=args.material_only,
        limit=args.limit,
    )
    print("ASSET INTELLIGENCE DIFF")
    print(f"Snapshots carregados: {summary['snapshots_count']}")
    print(f"Ativos comparados: {summary['diffs_count']}")
    print(f"Mudanças materiais: {summary['material_changes']}")
    print(f"Mudanças de governança: {summary['governance_changes']}")
    print(f"Mudanças de status: {summary['status_changes']}")
    print(f"Mudanças de valuation: {summary['valuation_changes']}")
    print(f"Mudanças de regime: {summary['regime_changes']}")
    if summary["rows_saved"]:
        print(f"Diffs salvos: {summary['rows_saved']}")
    if summary["alerts_saved"]:
        print(f"Alertas salvos: {summary['alerts_saved']}")
    if summary["csv_path"]:
        print(f"CSV: {summary['csv_path']}")
    if summary["diffs_count"] == 0:
        print("Histórico insuficiente: é necessário ter ao menos dois snapshots por ativo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
