"""Constrói histórico de snapshots de cadeia de opções a partir do SQLite/COTAHIST."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.db.init_db import init_database
from src.options.options_chain_normalizer import normalize_options_chain, validate_options_chain
from src.options.options_governance import evaluate_option_candidate
from src.options.options_history import get_available_option_history_range
from src.scanners.options_intelligence_scanner import enrich_options_chain
from src.utils import load_config, project_path


SNAPSHOT_COLUMNS = [
    "captured_at",
    "trade_date",
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "spread_pct",
    "volume",
    "trades",
    "financial_volume",
    "open_interest",
    "underlying_price",
    "moneyness_pct",
    "moneyness_class",
    "intrinsic_value",
    "extrinsic_value",
    "breakeven",
    "implied_volatility",
    "historical_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    "risk_score",
    "metadata_json",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_raw_option_history(db_path: Path, start: str | None, end: str | None, underlyings: list[str] | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    prefixes = [u[:4].upper() for u in underlyings or []]
    where = ["option_type IN ('CALL','PUT')"]
    params: list[Any] = []
    if start:
        where.append("trade_date >= ?")
        params.append(start)
    if end:
        where.append("trade_date <= ?")
        params.append(end)
    if prefixes:
        where.append("substr(ticker, 1, 4) IN (" + ",".join("?" for _ in prefixes) + ")")
        params.extend(prefixes)
    with sqlite3.connect(db_path) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cotahist_daily'").fetchone()
        if not exists:
            return pd.DataFrame()
        raw = pd.read_sql_query(f"SELECT * FROM cotahist_daily WHERE {' AND '.join(where)} ORDER BY trade_date, ticker", con, params=params)
        if raw.empty:
            return raw
        price_where = []
        price_params: list[Any] = []
        if start:
            price_where.append("trade_date >= ?")
            price_params.append(start)
        if end:
            price_where.append("trade_date <= ?")
            price_params.append(end)
        sql = "SELECT trade_date, ticker AS underlying, close AS underlying_price FROM cotahist_daily WHERE market_type IN ('010','10',10)"
        if price_where:
            sql += " AND " + " AND ".join(price_where)
        prices = pd.read_sql_query(sql, con, params=price_params)
    if underlyings:
        base_map = {u[:4].upper(): u.upper() for u in underlyings}
        raw["underlying"] = raw["ticker"].astype(str).str[:4].str.upper().map(base_map)
    else:
        raw["underlying"] = raw["ticker"].astype(str).str[:4].str.upper()
    if not prices.empty:
        raw = raw.merge(prices, on=["trade_date", "underlying"], how="left")
    return raw


def build_options_history(
    *,
    db_path: str | Path,
    start: str | None = None,
    end: str | None = None,
    underlyings: list[str] | None = None,
    risk_free_rate: float = 0.10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    db = Path(db_path)
    raw = _load_raw_option_history(db, start, end, underlyings)
    if raw.empty:
        coverage = pd.DataFrame([{"coverage_status": "SEM_DADOS", "snapshots_count": 0, "message": "Não foram encontrados dados históricos de cadeia de opções para o período/ativos informados."}])
        return pd.DataFrame(columns=SNAPSHOT_COLUMNS), coverage
    frames = []
    validations = []
    for trade_date, group in raw.groupby("trade_date"):
        chain = normalize_options_chain(group, reference_date=trade_date)
        valid, report = validate_options_chain(chain)
        validations.append(report.assign(trade_date=trade_date))
        enriched = enrich_options_chain(valid, risk_free_rate=risk_free_rate)
        enriched["trade_date"] = str(trade_date)
        enriched["captured_at"] = f"{trade_date}T18:00:00"
        reviews = [evaluate_option_candidate(row) for _, row in enriched.iterrows()]
        enriched["metadata_json"] = [
            json.dumps({"governance_status": r["governance_status"], "reasons": r["reasons"]}, ensure_ascii=False)
            for r in reviews
        ]
        frames.append(enriched)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    for col in SNAPSHOT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    coverage = pd.DataFrame(
        [
            {
                "min_date": out["trade_date"].min() if not out.empty else None,
                "max_date": out["trade_date"].max() if not out.empty else None,
                "underlyings_count": int(out["underlying"].nunique()) if not out.empty else 0,
                "options_count": int(out["option_ticker"].nunique()) if not out.empty else 0,
                "snapshots_count": int(len(out)),
                "validation_issues": int(pd.concat(validations)["count"].sum()) if validations else 0,
                "coverage_status": "COBERTURA_FRACA" if len(out) < 500 else "COBERTURA_MEDIA",
            }
        ]
    )
    return out[SNAPSHOT_COLUMNS], coverage


def _save_snapshots(db_path: Path, snapshots: pd.DataFrame) -> int:
    if snapshots.empty:
        return 0
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        snapshots[SNAPSHOT_COLUMNS].to_sql("options_chain_snapshots", con, if_exists="append", index=False)
        con.commit()
    return len(snapshots)


def _write_csv(snapshots: pd.DataFrame, coverage: pd.DataFrame) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "snapshots": reports / f"options_history_snapshots_{stamp}.csv",
        "coverage": reports / f"options_history_coverage_{stamp}.csv",
    }
    snapshots.to_csv(paths["snapshots"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    coverage.to_csv(paths["coverage"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    underlyings: list[str] | None = None,
    save_db: bool = False,
    write_csv: bool = False,
    source: str = "sqlite",
    risk_free_rate: float = 0.10,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    snapshots, coverage = build_options_history(db_path=db, start=start, end=end, underlyings=underlyings, risk_free_rate=risk_free_rate)
    saved = _save_snapshots(db, snapshots) if save_db and not snapshots.empty else 0
    paths = _write_csv(snapshots, coverage) if write_csv else {}
    if snapshots.empty:
        print("Não foram encontrados dados históricos de cadeia de opções para o período/ativos informados.")
    print("\nOPTIONS HISTORY BUILDER")
    print(f"Fonte: {source}")
    print(f"Snapshots gerados: {len(snapshots)}")
    print(f"Snapshots salvos: {saved}")
    print(f"Cobertura: {coverage.iloc[0].get('coverage_status') if not coverage.empty else 'SEM_DADOS'}")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {"snapshots": snapshots, "coverage": coverage, "saved": saved, "csv_paths": paths, "range": get_available_option_history_range(db)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrói histórico de cadeia de opções.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--underlyings", nargs="*", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--source", default="sqlite")
    parser.add_argument("--risk-free-rate", type=float, default=0.10)
    args = parser.parse_args()
    run(start=args.start, end=args.end, underlyings=args.underlyings, save_db=args.save_db, write_csv=args.write_csv, source=args.source, risk_free_rate=args.risk_free_rate)


if __name__ == "__main__":
    main()
