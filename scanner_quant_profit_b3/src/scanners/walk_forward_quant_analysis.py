"""CLI de walk-forward para validar o score quantitativo fora da amostra."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.quant.net_backtest import apply_execution_costs_to_backtest
from src.quant.walk_forward import run_walk_forward_analysis, summarize_walk_forward_results
from src.reports.quant_dashboard_data import load_backtest_results
from src.utils import load_config, project_path


def _filter_dates(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["_trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    if start:
        out = out[out["_trade_date"] >= pd.to_datetime(start)]
    if end:
        out = out[out["_trade_date"] <= pd.to_datetime(end)]
    return out.drop(columns=["_trade_date"]).reset_index(drop=True)


def _write_csv(walk_df: pd.DataFrame, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"walk_forward_results_{stamp}.csv"
    walk_df.to_csv(path, index=False, sep=";", decimal=",")
    return path


def _save_walk_forward_run(
    *,
    db_path: Path,
    walk_df: pd.DataFrame,
    summary: dict,
    start: str | None,
    end: str | None,
    train_months: int,
    test_months: int,
    horizon: int,
    net_mode: bool = False,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO walk_forward_runs (
                created_at, start_date, end_date, train_months, test_months, horizon,
                windows_count, positive_windows_pct, mean_test_return,
                mean_test_hit_rate, overfitting_alert, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                start,
                end,
                train_months,
                test_months,
                horizon,
                summary.get("windows_count", 0),
                summary.get("positive_windows_pct", 0.0),
                summary.get("mean_test_return", 0.0),
                summary.get("mean_test_hit_rate", 0.0),
                int(bool(summary.get("overfitting_alert", False))),
                json.dumps({**summary, "net_mode": net_mode}, ensure_ascii=False, default=str),
            ),
        )
        run_id = int(cur.lastrowid)

        for _, row in walk_df.iterrows():
            cur.execute(
                """
                INSERT INTO walk_forward_results (
                    run_id, window_id, train_start, train_end, test_start, test_end,
                    best_train_signal_type, test_return_best_signal, test_hit_rate_best_signal,
                    best_train_score_bucket, test_return_best_bucket, test_hit_rate_best_bucket,
                    degradation_score, overfitting_flag, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row.get("window_id"),
                    row.get("train_start"),
                    row.get("train_end"),
                    row.get("test_start"),
                    row.get("test_end"),
                    row.get("best_train_signal_type"),
                    row.get("test_return_best_signal"),
                    row.get("test_hit_rate_best_signal"),
                    row.get("best_train_score_bucket"),
                    row.get("test_return_best_bucket"),
                    row.get("test_hit_rate_best_bucket"),
                    row.get("degradation_score"),
                    int(bool(row.get("overfitting_flag"))),
                    json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                ),
            )
        con.commit()
    return run_id


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    train_months: int = 12,
    test_months: int = 3,
    horizon: int = 5,
    write_csv: bool = False,
    save_db: bool = False,
    net: bool = False,
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
    min_volume: float = 5_000_000,
    only_tradeable: bool = False,
) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    backtest = _filter_dates(load_backtest_results(db_path), start, end)
    if backtest.empty:
        message = "Sem resultados históricos salvos. Rode historical_quant_backtest com --save-db antes do walk-forward."
        print(message)
        return {"walk_forward": pd.DataFrame(), "summary": {}, "message": message}

    if net and f"net_return_{horizon}d" not in backtest.columns:
        backtest = apply_execution_costs_to_backtest(
            backtest,
            cost_bps=cost_bps,
            slippage_bps=slippage_bps,
            min_volume=min_volume,
            only_tradeable=only_tradeable,
        )
    elif net and only_tradeable and "is_tradeable" in backtest.columns:
        backtest = backtest[backtest["is_tradeable"].astype(bool)].reset_index(drop=True)

    return_prefix = "net_return" if net else "future_return"
    walk_df = run_walk_forward_analysis(
        backtest,
        train_months=train_months,
        test_months=test_months,
        horizon=horizon,
        return_prefix=return_prefix,
        only_tradeable=only_tradeable,
    )
    summary = summarize_walk_forward_results(walk_df)

    print("\nWALK-FORWARD DO SCORE QUANTITATIVO")
    print("Modo de retorno: líquido" if net else "Modo de retorno: bruto")
    print(summary["relatorio"])
    if not walk_df.empty:
        cols = [
            "window_id",
            "train_start",
            "train_end",
            "test_start",
            "test_end",
            "best_train_signal_type",
            "test_return_best_signal",
            "best_train_score_bucket",
            "test_return_best_bucket",
            "degradation_score",
            "overfitting_flag",
        ]
        print("\nJanelas:")
        print(walk_df[[c for c in cols if c in walk_df.columns]].to_string(index=False))

    csv_path = None
    if write_csv and not walk_df.empty:
        csv_path = _write_csv(walk_df, project_path("data/reports"))
        print(f"\nCSV gerado: {csv_path}")

    run_id = None
    if save_db and not walk_df.empty:
        run_id = _save_walk_forward_run(
            db_path=db_path,
            walk_df=walk_df,
            summary=summary,
            start=start,
            end=end,
            train_months=train_months,
            test_months=test_months,
            horizon=horizon,
            net_mode=net,
        )
        print(f"\nWalk-forward salvo no banco. run_id={run_id}")

    return {"walk_forward": walk_df, "summary": summary, "csv_path": csv_path, "run_id": run_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward fora da amostra do score quantitativo.")
    parser.add_argument("--start", default=None, help="Data inicial YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Data final YYYY-MM-DD.")
    parser.add_argument("--train-months", type=int, default=12, help="Meses na janela de treino.")
    parser.add_argument("--test-months", type=int, default=3, help="Meses na janela de teste.")
    parser.add_argument("--horizon", type=int, default=5, help="Horizonte de retorno futuro usado na análise.")
    parser.add_argument("--csv", action="store_true", help="Salva CSV por janela em data/reports.")
    parser.add_argument("--save-db", action="store_true", help="Salva resultados em walk_forward_* no SQLite.")
    parser.add_argument("--net", action="store_true", help="Usa retorno líquido quando disponível ou calcula custos antes da análise.")
    parser.add_argument("--cost-bps", type=float, default=10.0, help="Custo estimado por ponta em basis points.")
    parser.add_argument("--slippage-bps", type=float, default=5.0, help="Slippage estimado por ponta em basis points.")
    parser.add_argument("--min-volume", type=float, default=5_000_000, help="Volume mínimo para modo líquido.")
    parser.add_argument("--only-tradeable", action="store_true", help="Usa apenas sinais negociáveis no modo líquido.")
    args = parser.parse_args()

    run(
        start=args.start,
        end=args.end,
        train_months=args.train_months,
        test_months=args.test_months,
        horizon=args.horizon,
        write_csv=args.csv,
        save_db=args.save_db,
        net=args.net,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        min_volume=args.min_volume,
        only_tradeable=args.only_tradeable,
    )


if __name__ == "__main__":
    main()
