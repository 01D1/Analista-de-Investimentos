"""CLI para análise e persistência de regimes de mercado."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.quant.historical_loader import load_daily_prices
from src.quant.market_regimes import build_market_proxy_from_universe, calculate_market_regime_features
from src.quant.regime_backtest import generate_regime_report, summarize_backtest_by_regime
from src.utils import load_config, project_path


def _write_csv(regimes: pd.DataFrame, summary: pd.DataFrame, reports_dir: Path) -> dict[str, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "regimes": reports_dir / f"market_regimes_{stamp}.csv",
    }
    regimes.to_csv(paths["regimes"], index=False, sep=";", decimal=",")
    if summary is not None and not summary.empty:
        paths["summary"] = reports_dir / f"regime_backtest_summary_{stamp}.csv"
        summary.to_csv(paths["summary"], index=False, sep=";", decimal=",")
    return paths


def _save_regimes(db_path: Path, regimes: pd.DataFrame) -> None:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        for _, row in regimes.iterrows():
            cur.execute(
                """
                INSERT INTO market_regime_daily (
                    trade_date, primary_regime, trend_regime, volatility_regime,
                    liquidity_regime, risk_regime, regime_confidence,
                    market_return_mean, market_return_median, pct_assets_positive,
                    total_volume, universe_volatility, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("trade_date"),
                    row.get("primary_regime"),
                    row.get("trend_regime"),
                    row.get("volatility_regime"),
                    row.get("liquidity_regime"),
                    row.get("risk_regime"),
                    row.get("regime_confidence"),
                    row.get("market_return_mean"),
                    row.get("market_return_median"),
                    row.get("pct_assets_positive"),
                    row.get("total_volume"),
                    row.get("universe_volatility"),
                    json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                ),
            )
        con.commit()


def _latest_backtest_with_regimes(db_path: Path, start: str | None, end: str | None) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    where = ["primary_regime IS NOT NULL"]
    params: list[str] = []
    if start:
        where.append("trade_date >= ?")
        params.append(start)
    if end:
        where.append("trade_date <= ?")
        params.append(end)
    try:
        with sqlite3.connect(db_path) as con:
            exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='historical_backtest_results'").fetchone()
            if exists is None:
                return pd.DataFrame()
            run = con.execute(
                "SELECT MAX(run_id) FROM historical_backtest_results WHERE primary_regime IS NOT NULL"
            ).fetchone()
            if run is None or run[0] is None:
                return pd.DataFrame()
            where.append("run_id = ?")
            params.append(int(run[0]))
            sql = "SELECT * FROM historical_backtest_results WHERE " + " AND ".join(where)
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def _save_summary(db_path: Path, summary: pd.DataFrame, run_id: int | None = None) -> None:
    if summary is None or summary.empty:
        return
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        for _, row in summary.iterrows():
            cur.execute(
                """
                INSERT INTO regime_backtest_summary (
                    run_id, regime_type, regime_value, signals_count,
                    mean_gross_return_5d, mean_net_return_5d, hit_rate_5d,
                    tradeable_pct, top_asset_concentration_pct,
                    best_signal_type, best_score_bucket, robustness_class, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row.get("regime_type"),
                    row.get("regime_value"),
                    row.get("signals_count"),
                    row.get("mean_gross_return_5d"),
                    row.get("mean_net_return_5d"),
                    row.get("hit_rate_5d"),
                    row.get("tradeable_pct"),
                    row.get("top_asset_concentration_pct"),
                    row.get("best_signal_type"),
                    row.get("best_score_bucket"),
                    row.get("robustness_class"),
                    json.dumps(row.to_dict(), ensure_ascii=False, default=str),
                ),
            )
        con.commit()


def run(*, start: str | None = None, end: str | None = None, save_db: bool = False, write_csv: bool = False) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    prices = load_daily_prices(db_path, start_date=start, end_date=end)
    if prices.empty:
        message = prices.attrs.get("mensagem", "Sem preços históricos para regimes.")
        print(message)
        return {"message": message, "regimes": pd.DataFrame(), "summary": pd.DataFrame()}
    proxy = build_market_proxy_from_universe(prices)
    regimes = calculate_market_regime_features(proxy)
    backtest = _latest_backtest_with_regimes(db_path, start, end)
    summary = summarize_backtest_by_regime(backtest) if not backtest.empty else pd.DataFrame()

    print("\nREGIMES DE MERCADO")
    if not regimes.empty:
        latest = regimes.iloc[-1]
        print(
            f"Último regime: {latest.get('primary_regime')} | tendência={latest.get('trend_regime')} | "
            f"volatilidade={latest.get('volatility_regime')} | liquidez={latest.get('liquidity_regime')}"
        )
    if not summary.empty:
        print(generate_regime_report(summary))

    paths = {}
    if write_csv:
        paths = _write_csv(regimes, summary, project_path("data/reports"))
        for name, path in paths.items():
            print(f"- {name}: {path}")
    if save_db:
        _save_regimes(db_path, regimes)
        _save_summary(db_path, summary)
        print("Regimes salvos no banco.")
    return {"prices": prices, "proxy": proxy, "regimes": regimes, "summary": summary, "csv_paths": paths}


def main() -> None:
    parser = argparse.ArgumentParser(description="Análise de regimes de mercado.")
    parser.add_argument("--start", default=None, help="Data inicial YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Data final YYYY-MM-DD.")
    parser.add_argument("--save-db", action="store_true", help="Salva regimes no SQLite.")
    parser.add_argument("--csv", action="store_true", help="Salva CSV em data/reports.")
    args = parser.parse_args()
    run(start=args.start, end=args.end, save_db=args.save_db, write_csv=args.csv)


if __name__ == "__main__":
    main()
