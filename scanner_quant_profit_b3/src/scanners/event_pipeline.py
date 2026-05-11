"""Pipeline local de eventos: conectores, normalização, dedupe e cobertura."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.context.connectors import (
    cvm_connector,
    local_csv_connector,
    macro_calendar_connector,
    manual_events_connector,
    news_hunter_connector,
    releases_connector,
)
from src.context.event_coverage import calculate_event_coverage
from src.context.event_normalizer import merge_duplicate_events, normalize_events
from src.context.event_importer import save_events_to_db
from src.db.init_db import init_database
from src.utils import load_config, project_path


CONNECTORS = {
    "csv": local_csv_connector,
    "manual": manual_events_connector,
    "news_hunter": news_hunter_connector,
    "cvm": cvm_connector,
    "releases": releases_connector,
    "macro_calendar": macro_calendar_connector,
}


def _load_signals(db_path: Path, start: str | None, end: str | None, tickers: list[str] | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    clauses = []
    params: list = []
    if start:
        clauses.append("trade_date >= ?")
        params.append(start)
    if end:
        clauses.append("trade_date <= ?")
        params.append(end)
    if tickers:
        clean = [ticker.upper() for ticker in tickers]
        clauses.append(f"ticker IN ({', '.join(['?'] * len(clean))})")
        params.extend(clean)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='historical_backtest_results'").fetchone()
            if not exists:
                return pd.DataFrame()
            existing_cols = {row[1] for row in con.execute("PRAGMA table_info(historical_backtest_results)").fetchall()}
            wanted = [
                "trade_date",
                "ticker",
                "primary_regime",
                "trend_regime",
                "volatility_regime",
                "liquidity_regime",
                "risk_regime",
            ]
            cols = [col for col in wanted if col in existing_cols]
            return pd.read_sql_query(f"SELECT {', '.join(cols)} FROM historical_backtest_results {where}", con, params=params)
    except Exception:
        return pd.DataFrame()


def _write_csvs(events: pd.DataFrame, coverage: dict) -> dict[str, Path]:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    events_path = reports_dir / f"event_pipeline_events_{stamp}.csv"
    coverage_path = reports_dir / f"event_coverage_report_{stamp}.csv"
    events.to_csv(events_path, index=False, sep=";", decimal=",")
    pd.DataFrame([coverage]).to_csv(coverage_path, index=False, sep=";", decimal=",")
    return {"events": events_path, "coverage": coverage_path}


def _save_coverage_run(
    db_path: Path,
    *,
    start: str | None,
    end: str | None,
    sources: list[str],
    events_loaded: int,
    events_after_dedup: int,
    coverage: dict,
    metadata: dict | None = None,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO event_coverage_runs (
                created_at, start_date, end_date, sources, events_loaded, events_after_dedup,
                tickers_count, signals_count, signals_with_event_pct,
                tickers_with_event_pct, coverage_quality, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                start,
                end,
                ",".join(sources),
                int(events_loaded),
                int(events_after_dedup),
                int(len(coverage.get("tickers_with_events", [])) + len(coverage.get("tickers_without_events", []))),
                int(coverage.get("total_signals", 0)),
                float(coverage.get("signals_with_event_pct", 0)),
                float(coverage.get("tickers_with_event_pct", 0)),
                coverage.get("coverage_quality"),
                json.dumps({"coverage": coverage, **(metadata or {})}, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def _load_from_sources(
    sources: list[str],
    start: str | None,
    end: str | None,
    tickers: list[str] | None,
    csv_path: str | None,
    source_options: dict[str, dict] | None = None,
) -> pd.DataFrame:
    frames = []
    source_options = source_options or {}
    for source in sources:
        connector = CONNECTORS.get(source)
        if connector is None:
            continue
        kwargs = {"start_date": start, "end_date": end, "tickers": tickers}
        if source in {"csv", "manual"}:
            kwargs["csv_path"] = csv_path
        kwargs.update(source_options.get(source, {}))
        df = connector.load_events(**kwargs)
        if df is not None and not df.empty:
            if "event_source" not in df.columns:
                df["event_source"] = source
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    sources: list[str] | None = None,
    csv_path: str | None = None,
    save_db: bool = False,
    write_csv: bool = False,
    dedupe: bool = True,
    classify: bool = True,
    coverage: bool = True,
    db_path: str | Path | None = None,
    source_options: dict[str, dict] | None = None,
) -> dict:
    if db_path is None:
        cfg = load_config()
        db_path = project_path(cfg["database_path"])
    db_path = Path(db_path)
    sources = sources or ["csv"]
    loaded = _load_from_sources(sources, start, end, tickers, csv_path, source_options=source_options)
    normalized = normalize_events(loaded) if classify else loaded.copy()
    final_events = merge_duplicate_events(normalized) if dedupe else normalized
    final_events["normalized_at"] = datetime.now().isoformat(timespec="seconds") if not final_events.empty else pd.Series(dtype=str)
    signals = _load_signals(db_path, start, end, tickers)
    coverage_metrics = calculate_event_coverage(final_events, signals, tickers=tickers) if coverage else {}

    paths = {}
    if write_csv:
        paths = _write_csvs(final_events, coverage_metrics)
    saved = 0
    coverage_run_id = None
    if save_db:
        saved = save_events_to_db(final_events, db_path)
        coverage_run_id = _save_coverage_run(
            db_path,
            start=start,
            end=end,
            sources=sources,
            events_loaded=len(loaded),
            events_after_dedup=len(final_events),
            coverage=coverage_metrics,
            metadata={"csv_path": csv_path, "dedupe": dedupe, "classify": classify},
        )

    print("\nPIPELINE DE EVENTOS")
    print(f"Fontes: {', '.join(sources)}")
    print(f"Eventos carregados: {len(loaded)}")
    print(f"Eventos apos dedupe: {len(final_events)}")
    if coverage_metrics:
        print(f"Cobertura: {coverage_metrics.get('coverage_quality')} | sinais cobertos: {coverage_metrics.get('signals_with_event_pct', 0):.1%}")
    if save_db:
        print(f"Eventos salvos: {saved}; event_coverage_run_id={coverage_run_id}")
    if write_csv:
        print("CSVs gerados:")
        for name, path in paths.items():
            print(f"- {name}: {path}")
    return {
        "events": final_events,
        "events_loaded": len(loaded),
        "events_after_dedup": len(final_events),
        "coverage": coverage_metrics,
        "csv_paths": paths,
        "saved": saved,
        "coverage_run_id": coverage_run_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline local de eventos para market_events.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--sources", nargs="*", default=["csv"], choices=sorted(CONNECTORS))
    parser.add_argument("--csv-path", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--dedupe", action="store_true", default=True)
    parser.add_argument("--no-dedupe", action="store_false", dest="dedupe")
    parser.add_argument("--classify", action="store_true", default=True)
    parser.add_argument("--no-classify", action="store_false", dest="classify")
    parser.add_argument("--coverage", action="store_true", default=True)
    parser.add_argument("--no-coverage", action="store_false", dest="coverage")
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        tickers=args.tickers,
        sources=args.sources,
        csv_path=args.csv_path,
        save_db=args.save_db,
        write_csv=args.write_csv,
        dedupe=args.dedupe,
        classify=args.classify,
        coverage=args.coverage,
    )


if __name__ == "__main__":
    main()
