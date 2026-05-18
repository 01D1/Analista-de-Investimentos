"""CLI para gerar snapshot integrado por ativo."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.integration.asset_intelligence_engine import build_asset_intelligence_snapshot
from src.integration.asset_intelligence_store import save_asset_intelligence_snapshot
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(df: pd.DataFrame) -> Path | None:
    if df.empty:
        return None
    path = _reports_dir() / f"asset_intelligence_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def run(
    tickers: list[str] | None,
    trade_date: str | None = None,
    save_db: bool = False,
    csv: bool = False,
    include_technical: bool = True,
    include_quant: bool = True,
    include_valuation: bool = True,
    include_events: bool = True,
    include_regimes: bool = True,
    include_options: bool = True,
    include_risk: bool = True,
    db_path: str | Path | None = None,
    valuation_base_path: str | Path | None = None,
) -> dict:
    cfg = load_config()
    db = Path(db_path) if db_path else project_path(cfg["database_path"])
    df = build_asset_intelligence_snapshot(
        tickers=tickers,
        trade_date=trade_date,
        db_path=db,
        valuation_base_path=valuation_base_path,
        include_technical=include_technical,
        include_quant=include_quant,
        include_valuation=include_valuation,
        include_events=include_events,
        include_regimes=include_regimes,
        include_options=include_options,
        include_risk=include_risk,
    )
    saved = 0
    if save_db:
        init_database(db, verbose=False)
        saved = save_asset_intelligence_snapshot(db, df)
    csv_path = _write_csv(df) if csv else None
    summary = {
        "assets_count": int(len(df)),
        "with_technical": int(df["technical_score_final"].notna().sum()) if not df.empty else 0,
        "with_quant": int(df["quant_score"].notna().sum()) if not df.empty else 0,
        "with_valuation": int(df["valuation_available"].fillna(False).astype(bool).sum()) if not df.empty else 0,
        "with_options": int(df["option_available"].fillna(False).astype(bool).sum()) if not df.empty else 0,
        "with_risk": int(df["risk_status"].notna().sum()) if not df.empty and "risk_status" in df.columns else 0,
        "governance_blocked": int(df["governance_blocked"].fillna(False).astype(bool).sum()) if not df.empty else 0,
        "high_convergence": int((df["integrated_status"] == "ALTA_CONVERGENCIA_ANALITICA").sum()) if not df.empty else 0,
        "insufficient_data": int(df["integrated_status"].astype(str).str.contains("DADOS|SEM_DADOS", na=False).sum()) if not df.empty else 0,
        "rows_saved": saved,
        "csv_path": str(csv_path) if csv_path else "",
        "data": df,
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera snapshot integrado por ativo.")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--trade-date", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--include-technical", action="store_true", default=True)
    parser.add_argument("--include-quant", action="store_true", default=True)
    parser.add_argument("--include-valuation", action="store_true", default=True)
    parser.add_argument("--include-events", action="store_true", default=True)
    parser.add_argument("--include-regimes", action="store_true", default=True)
    parser.add_argument("--include-options", action="store_true", default=True)
    parser.add_argument("--include-risk", action="store_true", default=True)
    parser.add_argument("--valuation-base-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(
        tickers=args.tickers,
        trade_date=args.trade_date,
        save_db=args.save_db,
        csv=args.csv,
        include_technical=args.include_technical,
        include_quant=args.include_quant,
        include_valuation=args.include_valuation,
        include_events=args.include_events,
        include_regimes=args.include_regimes,
        include_options=args.include_options,
        include_risk=args.include_risk,
        valuation_base_path=args.valuation_base_path,
    )
    print("ASSET INTELLIGENCE SNAPSHOT")
    print(f"Ativos analisados: {summary['assets_count']}")
    print(f"Com técnico: {summary['with_technical']}")
    print(f"Com quant: {summary['with_quant']}")
    print(f"Com valuation: {summary['with_valuation']}")
    print(f"Com opções: {summary['with_options']}")
    print(f"Com risco: {summary.get('with_risk', 0)}")
    print(f"Bloqueados por governança: {summary['governance_blocked']}")
    print(f"Alta convergência: {summary['high_convergence']}")
    print(f"Dados insuficientes: {summary['insufficient_data']}")
    if summary["rows_saved"]:
        print(f"Linhas salvas: {summary['rows_saved']}")
    if summary["csv_path"]:
        print(f"CSV: {summary['csv_path']}")
    if summary["assets_count"] == 0:
        print("Nenhum dado integrado encontrado para os filtros informados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
