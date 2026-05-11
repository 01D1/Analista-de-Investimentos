"""Rotina operacional para atualizar eventos e cobertura por regime."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.context.event_coverage import calculate_event_coverage_by_regime, classify_regime_event_coverage
from src.context.event_importer import save_events_to_db
from src.db.init_db import init_database
from src.scanners.event_pipeline import CONNECTORS, _load_from_sources, _load_signals, _save_coverage_run
from src.context.event_coverage import calculate_event_coverage
from src.context.event_normalizer import merge_duplicate_events, normalize_events
from src.utils import load_config, project_path


DEFAULT_CONFIG = {
    "sources": {
        "csv": {"enabled": True, "path": "data/events/market_events_example.csv"},
        "news_hunter": {"enabled": True, "db_path": "../12_PYTHON/news_hunter/banco.db"},
        "macro_calendar": {"enabled": True, "path": "../12_PYTHON/news_hunter/dados/calendario_economico.json"},
        "cvm": {"enabled": True, "base_dir": "../12_PYTHON/pipeline banco completo/data/qualitative/processed"},
        "releases": {"enabled": True, "base_dir": "../12_PYTHON/pipeline banco completo/data/qualitative/events"},
    },
    "coverage": {
        "min_signals_with_event_pct": 10,
        "min_tickers_with_event_pct": 30,
        "min_sources_count": 2,
    },
}


def _resolve(path_value: str | None, base: Path | None = None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    root = base or Path(__file__).resolve().parents[2]
    return (root / path).resolve()


def load_events_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path(__file__).resolve().parents[2] / "config" / "events.yaml"
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if path.exists():
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for section, value in loaded.items():
                if isinstance(value, dict) and isinstance(config.get(section), dict):
                    config[section].update(value)
                else:
                    config[section] = value
        except Exception:
            pass
    return config


def _enabled_sources(config: dict[str, Any]) -> list[str]:
    sources = []
    for name, opts in (config.get("sources") or {}).items():
        if opts is None or bool(opts.get("enabled", False)):
            if name in CONNECTORS:
                sources.append(name)
    return sources


def _source_options(config: dict[str, Any], csv_path: str | None = None) -> tuple[str | None, dict[str, dict]]:
    opts: dict[str, dict] = {}
    src = config.get("sources") or {}
    csv_cfg = src.get("csv") or {}
    resolved_csv = csv_path or str(_resolve(csv_cfg.get("path"))) if csv_cfg.get("path") else csv_path
    news_path = _resolve((src.get("news_hunter") or {}).get("db_path"))
    macro_path = _resolve((src.get("macro_calendar") or {}).get("path"))
    cvm_root = _resolve((src.get("cvm") or {}).get("base_dir"))
    releases_root = _resolve((src.get("releases") or {}).get("base_dir"))
    if news_path is not None:
        opts["news_hunter"] = {"db_path": news_path}
    if macro_path is not None:
        opts["macro_calendar"] = {"path": macro_path}
    if cvm_root is not None:
        opts["cvm"] = {"root_path": cvm_root}
    if releases_root is not None:
        opts["releases"] = {"root_path": releases_root}
    return resolved_csv, opts


def _load_regimes(db_path: Path, start: str | None, end: str | None) -> pd.DataFrame:
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
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_regime_daily'").fetchone()
            if not exists:
                return pd.DataFrame()
            return pd.read_sql_query(f"SELECT * FROM market_regime_daily {where}", con, params=params)
    except Exception:
        return pd.DataFrame()


def _save_coverage_by_regime(db_path: Path, coverage_run_id: int | None, coverage_by_regime: pd.DataFrame) -> int:
    if coverage_run_id is None or coverage_by_regime is None or coverage_by_regime.empty:
        return 0
    init_database(db_path, verbose=False)
    rows = []
    for _, row in coverage_by_regime.iterrows():
        rows.append(
            (
                int(coverage_run_id),
                row.get("regime_type"),
                row.get("regime_value"),
                int(row.get("signals_count") or 0),
                int(row.get("signals_with_event") or 0),
                int(row.get("signals_without_event") or 0),
                float(row.get("signals_with_event_pct") or 0),
                row.get("dominant_event_type"),
                row.get("dominant_event_source"),
                row.get("coverage_quality"),
                json.dumps({"source": "event_daily_update"}, ensure_ascii=False),
            )
        )
    with sqlite3.connect(db_path) as con:
        con.executemany(
            """
            INSERT INTO event_coverage_by_regime (
                coverage_run_id, regime_type, regime_value, signals_count,
                signals_with_event, signals_without_event, signals_with_event_pct,
                dominant_event_type, dominant_event_source, coverage_quality, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
    return len(rows)


def _write_csvs(events: pd.DataFrame, coverage: dict, coverage_by_regime: pd.DataFrame) -> dict[str, Path]:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "events": reports_dir / f"daily_event_update_events_{stamp}.csv",
        "coverage": reports_dir / f"daily_event_coverage_{stamp}.csv",
        "coverage_by_regime": reports_dir / f"daily_event_coverage_by_regime_{stamp}.csv",
    }
    events.to_csv(paths["events"], index=False, sep=";", decimal=",")
    pd.DataFrame([coverage]).to_csv(paths["coverage"], index=False, sep=";", decimal=",")
    coverage_by_regime.to_csv(paths["coverage_by_regime"], index=False, sep=";", decimal=",")
    return paths


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    sources: list[str] | None = None,
    tickers: list[str] | None = None,
    csv_path: str | None = None,
    save_db: bool = False,
    write_csv: bool = False,
    with_regimes: bool = False,
    dry_run: bool = False,
    db_path: str | Path | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    cfg = load_events_config(config_path)
    if db_path is None:
        main_cfg = load_config()
        db_path = project_path(main_cfg["database_path"])
    db_path = Path(db_path)
    csv_path_resolved, source_options = _source_options(cfg, csv_path=csv_path)
    selected_sources = sources or _enabled_sources(cfg)
    loaded = _load_from_sources(selected_sources, start, end, tickers, csv_path_resolved, source_options=source_options)
    normalized = normalize_events(loaded)
    events = merge_duplicate_events(normalized)
    if not events.empty:
        events["normalized_at"] = datetime.now().isoformat(timespec="seconds")
        events["coverage_source"] = ",".join(selected_sources)

    signals = _load_signals(db_path, start, end, tickers)
    coverage = calculate_event_coverage(events, signals, tickers=tickers)
    regimes = _load_regimes(db_path, start, end) if with_regimes else pd.DataFrame()
    coverage_by_regime = (
        classify_regime_event_coverage(calculate_event_coverage_by_regime(events, signals, regimes))
        if with_regimes
        else pd.DataFrame()
    )

    paths = _write_csvs(events, coverage, coverage_by_regime) if write_csv else {}
    saved_events = 0
    coverage_run_id = None
    regime_rows_saved = 0
    if save_db and not dry_run:
        saved_events = save_events_to_db(events, db_path)
        coverage_run_id = _save_coverage_run(
            db_path,
            start=start,
            end=end,
            sources=selected_sources,
            events_loaded=len(loaded),
            events_after_dedup=len(events),
            coverage=coverage,
            metadata={"routine": "event_daily_update", "with_regimes": with_regimes, "csv_path": csv_path_resolved},
        )
        regime_rows_saved = _save_coverage_by_regime(db_path, coverage_run_id, coverage_by_regime)

    print("\nROTINA DIARIA DE EVENTOS")
    print(f"Fontes: {', '.join(selected_sources)}")
    print(f"Eventos carregados: {len(loaded)}")
    print(f"Eventos apos dedupe: {len(events)}")
    print(f"Cobertura: {coverage.get('coverage_quality')} | sinais cobertos: {coverage.get('signals_with_event_pct', 0):.1%}")
    if with_regimes:
        print(f"Cobertura por regime: {len(coverage_by_regime)} linhas")
    if dry_run:
        print("Dry-run ativo: nada foi persistido no banco.")
    elif save_db:
        print(f"Eventos salvos: {saved_events}; event_coverage_run_id={coverage_run_id}; cobertura_regime_linhas={regime_rows_saved}")
    if write_csv:
        print("CSVs gerados:")
        for name, path in paths.items():
            print(f"- {name}: {path}")
    return {
        "events": events,
        "events_loaded": len(loaded),
        "events_after_dedup": len(events),
        "coverage": coverage,
        "coverage_by_regime": coverage_by_regime,
        "saved": saved_events,
        "coverage_run_id": coverage_run_id,
        "regime_rows_saved": regime_rows_saved,
        "csv_paths": paths,
        "sources": selected_sources,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotina diária/local de atualização de eventos e cobertura.")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--sources", nargs="*", default=None, choices=sorted(CONNECTORS))
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--csv-path", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--with-regimes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        sources=args.sources,
        tickers=args.tickers,
        csv_path=args.csv_path,
        save_db=args.save_db,
        write_csv=args.write_csv,
        with_regimes=args.with_regimes,
        dry_run=args.dry_run,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
