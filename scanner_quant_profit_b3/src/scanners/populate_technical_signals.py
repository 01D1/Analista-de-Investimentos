"""População histórica de sinais técnicos para estudo e validação de amostra."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.quant.historical_loader import load_daily_prices
from src.scanners.technical_analysis_scanner import build_technical_features, _prepare_setups, _save_features, _save_setups
from src.technical.setup_deduplication import deduplicate_setups
from src.utils import load_config, project_path


def _reports_dir() -> Path:
    path = project_path("data/reports")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(features: pd.DataFrame, setups: pd.DataFrame) -> dict[str, str]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "features": _reports_dir() / f"populated_technical_features_{stamp}.csv",
        "setups": _reports_dir() / f"populated_technical_setups_{stamp}.csv",
    }
    features.to_csv(paths["features"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    setups.to_csv(paths["setups"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return {k: str(v) for k, v in paths.items()}


def _delete_existing(con: sqlite3.Connection, table: str, start: str | None, end: str | None, tickers: list[str] | None) -> None:
    where = ["1=1"]
    params: list[object] = []
    if start:
        where.append("trade_date >= ?")
        params.append(start)
    if end:
        where.append("trade_date <= ?")
        params.append(end)
    if tickers:
        allowed = [str(t).upper() for t in tickers]
        where.append("UPPER(ticker) IN (" + ",".join(["?"] * len(allowed)) + ")")
        params.extend(allowed)
    con.execute(f"DELETE FROM {table} WHERE {' AND '.join(where)}", params)


def _save_dedup_run(con: sqlite3.Connection, summary: dict) -> None:
    con.execute(
        """
        INSERT INTO technical_setup_dedup_runs (
            created_at, signals_before, signals_after, removed_count,
            removed_pct, top_redundant_setups_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            int(summary.get("signals_before") or 0),
            int(summary.get("signals_after") or 0),
            int(summary.get("removed_count") or 0),
            float(summary.get("removed_pct") or 0),
            json.dumps(summary.get("top_redundant_setups", {}), ensure_ascii=False),
            json.dumps(summary, ensure_ascii=False, default=str),
        ),
    )


def run(
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    dedupe: bool = False,
    min_score: float | None = None,
    save_db: bool = False,
    csv: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    prices = load_daily_prices(db, tickers=tickers, start_date=start, end_date=end)
    diagnostics = []
    if prices.empty:
        diagnostics.append(prices.attrs.get("mensagem", "Dados insuficientes para população histórica técnica."))
        features = pd.DataFrame()
        setups = pd.DataFrame()
        dedup_summary = {"signals_before": 0, "signals_after": 0, "removed_count": 0, "removed_pct": 0.0}
    else:
        features = build_technical_features(prices)
        setups = _prepare_setups(features, None, min_score)
        dedup_summary = {"signals_before": int(len(setups)), "signals_after": int(len(setups)), "removed_count": 0, "removed_pct": 0.0}
        if dedupe and not setups.empty:
            setups, _, dedup_summary = deduplicate_setups(setups)
    csv_paths = _write_csv(features, setups) if csv else {}
    saved_features = 0
    saved_setups = 0
    if save_db and not dry_run:
        init_database(db, verbose=False)
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with sqlite3.connect(db) as con:
            _delete_existing(con, "technical_feature_snapshots", start, end, tickers)
            _delete_existing(con, "technical_setup_signals", start, end, tickers)
            _save_features(con, features, created_at)
            _save_setups(con, setups, created_at)
            if dedupe:
                _save_dedup_run(con, dedup_summary)
            con.commit()
        saved_features = int(len(features))
        saved_setups = int(len(setups))
    summary = {
        "status": "DRY_RUN" if dry_run else "SUCCESS",
        "features_count": int(len(features)),
        "setups_count": int(len(setups)),
        "saved_features_count": saved_features,
        "saved_setups_count": saved_setups,
        "tickers_count": int(features["ticker"].nunique()) if not features.empty and "ticker" in features.columns else 0,
        "active_days_count": int(features["trade_date"].nunique()) if not features.empty and "trade_date" in features.columns else 0,
        "dedup_summary": dedup_summary,
        "diagnostics": diagnostics,
        "csv_paths": csv_paths,
        "features": features,
        "setups": setups,
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Popula sinais técnicos históricos para estudo, sem recomendação.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--dedupe", action="store_true")
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(**vars(args))
    print("POPULAÇÃO HISTÓRICA TECHNICAL")
    print("Fonte de sinal em estudo: technical")
    print(f"Features geradas: {summary['features_count']}")
    print(f"Setups técnicos gerados: {summary['setups_count']}")
    print(f"Features persistidas: {summary['saved_features_count']}")
    print(f"Sinais technical persistidos: {summary['saved_setups_count']}")
    if summary["diagnostics"]:
        print("Diagnóstico: " + " | ".join(summary["diagnostics"]))
    if summary["csv_paths"]:
        print(f"CSVs: {summary['csv_paths']}")
    print("Não recomendação: rotina apenas popula e valida amostra histórica.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

