"""CLI para validar filtros de qualidade em walk-forward líquido."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.quant.filter_walk_forward import (
    generate_filter_walk_forward_report,
    run_filter_walk_forward,
    summarize_filter_walk_forward,
)
from src.utils import load_config, project_path


def _load_backtest_results(db_path: Path, start: str | None, end: str | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    where = []
    params: list[str] = []
    if start:
        where.append("trade_date >= ?")
        params.append(start)
    if end:
        where.append("trade_date <= ?")
        params.append(end)
    try:
        with sqlite3.connect(db_path) as con:
            tables = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='historical_backtest_results'"
            ).fetchone()
            if tables is None:
                return pd.DataFrame()
            run = con.execute(
                """
                SELECT id FROM historical_backtest_runs
                WHERE COALESCE(net_mode, 0) = 1
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if run is not None:
                where.append("run_id = ?")
                params.append(int(run[0]))
            sql = "SELECT * FROM historical_backtest_results"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY trade_date, ticker"
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def _has_net_returns(df: pd.DataFrame, objective: str) -> bool:
    col = objective.replace("mean_", "") if objective.startswith("mean_") else "net_return_5d"
    return col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().any()


def _write_csv(results: pd.DataFrame, reports_dir: Path) -> Path | None:
    if results.empty:
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"filter_walk_forward_results_{stamp}.csv"
    results.to_csv(path, index=False, sep=";", decimal=",")
    return path


def _save_run(
    *,
    db_path: Path,
    results: pd.DataFrame,
    summary: dict,
    start: str | None,
    end: str | None,
    train_months: int,
    test_months: int,
    objective: str,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO filter_walk_forward_runs (
                created_at, start_date, end_date, train_months, test_months, objective,
                windows_count, positive_windows_pct, mean_test_net_return, mean_test_hit_rate,
                avg_test_signals, avg_top_3_concentration_pct, robustness_class,
                overfitting_alert, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                start,
                end,
                train_months,
                test_months,
                objective,
                summary.get("windows_count"),
                summary.get("positive_windows_pct"),
                summary.get("mean_test_net_return"),
                summary.get("mean_test_hit_rate"),
                summary.get("avg_test_signals"),
                summary.get("avg_top_3_concentration_pct"),
                summary.get("robustness_class"),
                int(bool(summary.get("overfitting_alert"))),
                json.dumps(summary, ensure_ascii=False, default=str),
            ),
        )
        run_id = int(cur.lastrowid)
        for _, row in results.iterrows():
            cur.execute(
                """
                INSERT INTO filter_walk_forward_results (
                    run_id, window_id, train_start, train_end, test_start, test_end,
                    best_params_json, train_signals, test_signals,
                    train_mean_net_return, test_mean_net_return, train_hit_rate, test_hit_rate,
                    top_asset_concentration_pct, top_3_assets_concentration_pct,
                    positive_test_window, overfitting_flag, sample_warning,
                    concentration_warning, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row.get("window_id"),
                    row.get("train_start"),
                    row.get("train_end"),
                    row.get("test_start"),
                    row.get("test_end"),
                    row.get("best_params_json"),
                    row.get("train_signals"),
                    row.get("test_signals"),
                    row.get("train_mean_net_return"),
                    row.get("test_mean_net_return"),
                    row.get("train_hit_rate"),
                    row.get("test_hit_rate"),
                    row.get("top_asset_concentration_pct"),
                    row.get("top_3_assets_concentration_pct"),
                    int(bool(row.get("positive_test_window"))),
                    int(bool(row.get("overfitting_flag"))),
                    int(bool(row.get("sample_warning"))),
                    int(bool(row.get("concentration_warning"))),
                    json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                ),
            )
        con.commit()
    return run_id


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    train_months: int = 1,
    test_months: int = 1,
    objective: str = "mean_net_return_5d",
    min_samples_train: int = 100,
    min_samples_test: int = 30,
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
    min_volume: float = 5_000_000,
    write_csv: bool = False,
    save_db: bool = False,
) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    backtest = _load_backtest_results(db_path, start, end)
    if backtest.empty:
        message = "Sem historical_backtest_results no período informado. Rode historical_quant_backtest com --save-db."
        print(message)
        return {"results": pd.DataFrame(), "summary": {}, "message": message}
    if not _has_net_returns(backtest, objective):
        message = (
            "Colunas líquidas ausentes ou vazias. Rode: "
            "python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 "
            "--net --csv --save-db"
        )
        print(message)
        return {"results": pd.DataFrame(), "summary": {}, "message": message}

    results = run_filter_walk_forward(
        backtest,
        train_months=train_months,
        test_months=test_months,
        objective=objective,
        min_samples_train=min_samples_train,
        min_samples_test=min_samples_test,
    )
    summary = summarize_filter_walk_forward(results)
    report = generate_filter_walk_forward_report(summary, results)

    print("\nWALK-FORWARD DOS FILTROS")
    print(report)
    if not results.empty:
        print("\nResultados por janela:")
        cols = [
            "window_id",
            "train_start",
            "test_start",
            "train_signals",
            "test_signals",
            "train_mean_net_return",
            "test_mean_net_return",
            "test_hit_rate",
            "top_3_assets_concentration_pct",
            "overfitting_flag",
        ]
        print(results[[c for c in cols if c in results.columns]].to_string(index=False))

    csv_path = None
    if write_csv:
        csv_path = _write_csv(results, project_path("data/reports"))
        if csv_path:
            print(f"\nCSV gerado: {csv_path}")

    run_id = None
    if save_db:
        run_id = _save_run(
            db_path=db_path,
            results=results,
            summary=summary,
            start=start,
            end=end,
            train_months=train_months,
            test_months=test_months,
            objective=objective,
        )
        print(f"\nWalk-forward dos filtros salvo no banco. run_id={run_id}")

    return {
        "results": results,
        "summary": summary,
        "report": report,
        "csv_path": csv_path,
        "run_id": run_id,
        "execution_assumptions": {
            "cost_bps": cost_bps,
            "slippage_bps": slippage_bps,
            "min_volume": min_volume,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward líquido dos filtros de qualidade.")
    parser.add_argument("--start", default=None, help="Data inicial YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Data final YYYY-MM-DD.")
    parser.add_argument("--train-months", type=int, default=1, help="Meses de treino por janela.")
    parser.add_argument("--test-months", type=int, default=1, help="Meses de teste por janela.")
    parser.add_argument("--objective", default="mean_net_return_5d", help="Objetivo do grid, ex: mean_net_return_5d.")
    parser.add_argument("--min-samples-train", type=int, default=100, help="Amostra mínima no treino.")
    parser.add_argument("--min-samples-test", type=int, default=30, help="Amostra mínima no teste.")
    parser.add_argument("--cost-bps", type=float, default=10.0, help="Custo usado no backtest líquido de origem.")
    parser.add_argument("--slippage-bps", type=float, default=5.0, help="Slippage usado no backtest líquido de origem.")
    parser.add_argument("--min-volume", type=float, default=5_000_000, help="Volume mínimo usado no backtest líquido de origem.")
    parser.add_argument("--csv", action="store_true", help="Salva CSV em data/reports.")
    parser.add_argument("--save-db", action="store_true", help="Salva resultados no SQLite.")
    args = parser.parse_args()

    run(
        start=args.start,
        end=args.end,
        train_months=args.train_months,
        test_months=args.test_months,
        objective=args.objective,
        min_samples_train=args.min_samples_train,
        min_samples_test=args.min_samples_test,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        min_volume=args.min_volume,
        write_csv=args.csv,
        save_db=args.save_db,
    )


if __name__ == "__main__":
    main()
