"""CLI para vincular eventos importados aos sinais históricos salvos."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.context.event_importer import load_events_from_db, save_event_context_run
from src.quant.event_backtest import (
    compare_event_vs_no_event,
    generate_event_context_report,
    summarize_backtest_by_event_context,
)
from src.quant.event_linker import link_events_to_signals, save_signal_event_links
from src.utils import load_config, project_path


def _latest_backtest_run_id(con: sqlite3.Connection) -> int | None:
    row = con.execute("SELECT id FROM historical_backtest_runs ORDER BY id DESC LIMIT 1").fetchone()
    return int(row[0]) if row else None


def _load_backtest_results(db_path: Path, start: str | None, end: str | None, run_id: int | None = None) -> pd.DataFrame:
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
    with sqlite3.connect(db_path) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE name='historical_backtest_results' AND type='table'").fetchone()
        if not exists:
            return pd.DataFrame()
        selected_run_id = run_id if run_id is not None else _latest_backtest_run_id(con)
        if selected_run_id is not None:
            clauses.append("run_id = ?")
            params.append(int(selected_run_id))
            where = f"WHERE {' AND '.join(clauses)}"
        return pd.read_sql_query(f"SELECT * FROM historical_backtest_results {where} ORDER BY trade_date, ticker", con, params=params)


def _write_csvs(linked: pd.DataFrame, summary: pd.DataFrame) -> dict[str, Path]:
    reports_dir = project_path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "links": reports_dir / f"event_signal_links_{stamp}.csv",
        "summary": reports_dir / f"event_context_summary_{stamp}.csv",
    }
    linked.to_csv(paths["links"], index=False, sep=";", decimal=",")
    summary.to_csv(paths["summary"], index=False, sep=";", decimal=",")
    return paths


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    csv: bool = False,
    save_db: bool = False,
    event_window_before: int = 1,
    event_window_after: int = 1,
    run_id: int | None = None,
) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    events = load_events_from_db(db_path, start_date=start, end_date=end)
    signals = _load_backtest_results(db_path, start, end, run_id=run_id)
    if signals.empty:
        print("Nenhum historical_backtest_results encontrado. Rode o backtest com --save-db antes da análise de eventos.")
        return {"events": events, "signals": signals, "linked": pd.DataFrame(), "summary": pd.DataFrame()}
    linked = link_events_to_signals(signals, events, window_days_before=event_window_before, window_days_after=event_window_after)
    summary = summarize_backtest_by_event_context(linked)
    comparison = compare_event_vs_no_event(linked)
    report = generate_event_context_report(comparison)
    print("\nANÁLISE DE CONTEXTO DE EVENTOS")
    print(report)
    if not summary.empty:
        print(summary.head(20).to_string(index=False))
    paths = {}
    if csv:
        paths = _write_csvs(linked, summary)
        print("\nCSVs gerados:")
        for name, path in paths.items():
            print(f"- {name}: {path}")
    run_id = None
    links_saved = 0
    if save_db:
        links_saved = save_signal_event_links(linked, db_path)
        run_id = save_event_context_run(
            db_path=db_path,
            start_date=start,
            end_date=end,
            events_count=len(events),
            signals_linked=links_saved,
            tickers_count=int(linked["ticker"].nunique()) if "ticker" in linked else 0,
            source="event_context_analysis",
            metadata={"comparison": comparison, "window_before": event_window_before, "window_after": event_window_after, "run_id": run_id},
        )
        print(f"\nContexto de eventos salvo. event_context_run_id={run_id}; links_salvos={links_saved}")
    return {
        "events": events,
        "signals": signals,
        "linked": linked,
        "summary": summary,
        "comparison": comparison,
        "csv_paths": paths,
        "run_id": run_id,
        "links_saved": links_saved,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisa eventos importados contra sinais históricos salvos.")
    parser.add_argument("--start", default=None, help="Data inicial YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Data final YYYY-MM-DD.")
    parser.add_argument("--csv", action="store_true", help="Salva links e resumo em data/reports.")
    parser.add_argument("--save-db", action="store_true", help="Salva signal_event_links e event_context_runs.")
    parser.add_argument("--event-window-before", type=int, default=1, help="Dias antes do sinal aceitos para evento.")
    parser.add_argument("--event-window-after", type=int, default=1, help="Dias depois do sinal aceitos para evento.")
    parser.add_argument("--run-id", type=int, default=None, help="Run histórico específico. Se omitido, usa o último run salvo.")
    args = parser.parse_args()
    run(
        start=args.start,
        end=args.end,
        csv=args.csv,
        save_db=args.save_db,
        event_window_before=args.event_window_before,
        event_window_after=args.event_window_after,
        run_id=args.run_id,
    )


if __name__ == "__main__":
    main()
