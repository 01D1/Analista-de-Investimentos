"""CLI da camada opcional de analise tecnica quantitativa."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.quant.historical_loader import load_daily_prices
from src.technical.momentum import calculate_momentum_features
from src.technical.patterns import (
    detect_gap_down,
    detect_gap_up,
    detect_inside_bar,
    detect_outside_bar,
    detect_rejection_candle,
    detect_reversal_candle,
    detect_strength_candle,
    detect_wide_range_bar,
)
from src.technical.setups import detect_technical_setups
from src.technical.support_resistance import (
    calculate_support_resistance,
    detect_breakdown,
    detect_breakout,
    detect_near_resistance,
    detect_near_support,
)
from src.technical.technical_backtest import run_technical_setup_backtest, summarize_technical_backtest
from src.technical.technical_explanations import explain_technical_setup
from src.technical.technical_governance import evaluate_technical_setup_candidate
from src.technical.technical_score import calculate_technical_score
from src.technical.trend import calculate_trend_features
from src.technical.volatility import calculate_volatility_features
from src.technical.volume import calculate_volume_features
from src.utils import load_config, project_path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _apply_by_ticker(df: pd.DataFrame, func) -> pd.Series:
    parts = []
    for _, group in df.groupby("ticker", sort=False):
        series = func(group)
        series.index = group.index
        parts.append(series)
    return pd.concat(parts).sort_index() if parts else pd.Series(dtype=bool)


def build_technical_features(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return prices.copy()
    features = prices.sort_values(["ticker", "trade_date"]).reset_index(drop=True)
    features = calculate_trend_features(features)
    features = calculate_momentum_features(features)
    features = calculate_volatility_features(features)
    features = calculate_volume_features(features)
    features = features.groupby("ticker", group_keys=False).apply(lambda g: calculate_support_resistance(g)).reset_index(drop=True)
    features["breakout_20"] = _apply_by_ticker(features, lambda g: detect_breakout(g, 20)).astype(bool).to_numpy()
    features["breakdown_20"] = _apply_by_ticker(features, lambda g: detect_breakdown(g, 20)).astype(bool).to_numpy()
    features["near_support_20"] = _apply_by_ticker(features, lambda g: detect_near_support(g, 20)).astype(bool).to_numpy()
    features["near_resistance_20"] = _apply_by_ticker(features, lambda g: detect_near_resistance(g, 20)).astype(bool).to_numpy()
    pattern_funcs = {
        "inside_bar": detect_inside_bar,
        "outside_bar": detect_outside_bar,
        "wide_range_bar": detect_wide_range_bar,
        "gap_up": detect_gap_up,
        "gap_down": detect_gap_down,
        "reversal_candle": detect_reversal_candle,
        "strength_candle": detect_strength_candle,
        "rejection_candle": detect_rejection_candle,
    }
    for name, func in pattern_funcs.items():
        features[name] = _apply_by_ticker(features, func).astype(bool).to_numpy()
    return calculate_technical_score(features)


def _prepare_setups(features: pd.DataFrame, setups_filter: list[str] | None, min_score: float | None) -> pd.DataFrame:
    setups = detect_technical_setups(features, {"min_setup_score": min_score or 0})
    if setups_filter and not setups.empty:
        allowed = {s.upper() for s in setups_filter}
        setups = setups[setups["setup_type"].astype(str).str.upper().isin(allowed)]
    if setups.empty:
        return setups
    context_cols = [
        "trade_date",
        "ticker",
        "close",
        "high",
        "low",
        "open",
        "technical_score_final",
        "technical_status",
        "trend_short",
        "volatility_regime",
        "momentum_state",
    ]
    context = features[[c for c in context_cols if c in features.columns]].copy()
    context["trade_date"] = pd.to_datetime(context["trade_date"], errors="coerce").dt.date.astype(str)
    enriched = setups.merge(context, on=["trade_date", "ticker"], how="left")
    reviews = [evaluate_technical_setup_candidate({"signals": 0, "mean_return_5d": 0}) for _ in range(len(enriched))]
    enriched["governance_status"] = [review["governance_status"] for review in reviews]
    enriched["explanation"] = enriched.apply(explain_technical_setup, axis=1)
    return enriched


def _write_csv(features: pd.DataFrame, setups: pd.DataFrame, backtest: pd.DataFrame | None) -> dict[str, Path]:
    reports = project_path("data/reports")
    reports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "features": reports / f"technical_features_{stamp}.csv",
        "setups": reports / f"technical_setups_{stamp}.csv",
    }
    features.to_csv(paths["features"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    setups.to_csv(paths["setups"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    if backtest is not None:
        paths["backtest"] = reports / f"technical_backtest_{stamp}.csv"
        backtest.to_csv(paths["backtest"], index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return paths


def _save_features(con: sqlite3.Connection, features: pd.DataFrame, created_at: str) -> None:
    cols = [
        "created_at",
        "trade_date",
        "ticker",
        "trend_score",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "breakout_score",
        "support_resistance_score",
        "pattern_score",
        "risk_score",
        "technical_score_final",
        "technical_status",
        "metadata_json",
    ]
    if features.empty:
        return
    out = features.copy()
    out["created_at"] = created_at
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.date.astype(str)
    out["metadata_json"] = "{}"
    out[cols].to_sql("technical_feature_snapshots", con, if_exists="append", index=False)


def _save_setups(con: sqlite3.Connection, setups: pd.DataFrame, created_at: str) -> None:
    cols = [
        "created_at",
        "trade_date",
        "ticker",
        "setup_type",
        "setup_score",
        "setup_confidence",
        "setup_direction",
        "trigger_price",
        "invalidation_price",
        "target_hint",
        "risk_hint",
        "technical_status",
        "governance_status",
        "explanation",
        "reasons_for_json",
        "reasons_against_json",
        "metadata_json",
    ]
    if setups.empty:
        return
    out = setups.copy()
    out["created_at"] = created_at
    out["reasons_for_json"] = out.get("reasons_for")
    out["reasons_against_json"] = out.get("reasons_against")
    for col in cols:
        if col not in out.columns:
            out[col] = pd.NA
    out[cols].to_sql("technical_setup_signals", con, if_exists="append", index=False)


def _save_backtest(con: sqlite3.Connection, backtest: pd.DataFrame, summary: pd.DataFrame, started: str, finished: str, setup_type: str | None, start: str | None, end: str | None) -> int:
    row = summary.iloc[0].to_dict() if not summary.empty else {}
    governance = evaluate_technical_setup_candidate(row)
    con.execute(
        """
        INSERT INTO technical_backtest_runs (
            started_at, finished_at, status, setup_type, start_date, end_date,
            signals_count, mean_return_5d, hit_rate_5d, governance_status, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            started,
            finished,
            "SUCCESS" if not backtest.empty else "INSUFFICIENT_DATA",
            setup_type,
            start,
            end,
            int(row.get("signals") or len(backtest)),
            float(row.get("mean_return_5d") or 0),
            float(row.get("hit_rate_5d") or 0),
            governance["governance_status"],
            json.dumps({"summary_rows": len(summary)}, ensure_ascii=False),
        ),
    )
    run_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
    if not backtest.empty:
        result_cols = [
            "run_id",
            "trade_date",
            "ticker",
            "setup_type",
            "technical_score_final",
            "technical_status",
            "future_return_1d",
            "future_return_3d",
            "future_return_5d",
            "future_return_10d",
            "hit_1d",
            "hit_3d",
            "hit_5d",
            "hit_10d",
            "metadata_json",
        ]
        out = backtest.copy()
        out["run_id"] = run_id
        out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.date.astype(str)
        out["metadata_json"] = "{}"
        for col in result_cols:
            if col not in out.columns:
                out[col] = pd.NA
        out[result_cols].to_sql("technical_backtest_results", con, if_exists="append", index=False)
    return run_id


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    setups: list[str] | None = None,
    save_db: bool = False,
    write_csv: bool = False,
    with_backtest: bool = False,
    horizons: list[int] | None = None,
    min_score: float | None = None,
    dry_run: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    started = _now()
    db = Path(db_path) if db_path else project_path(load_config()["database_path"])
    prices = load_daily_prices(db, tickers=tickers, start_date=start, end_date=end)
    if prices.empty:
        print(prices.attrs.get("mensagem", "Nenhum dado diario encontrado para analise tecnica."))
        features = pd.DataFrame()
        setup_signals = pd.DataFrame()
        backtest = pd.DataFrame()
        summary = pd.DataFrame()
    else:
        features = build_technical_features(prices)
        setup_signals = _prepare_setups(features, setups, min_score)
        if with_backtest and not setup_signals.empty:
            labels = setup_signals[["trade_date", "ticker", "setup_type", "setup_score", "setup_confidence"]].copy()
            labels["trade_date"] = pd.to_datetime(labels["trade_date"], errors="coerce").dt.date.astype(str)
            bt_input = features.copy()
            bt_input["trade_date"] = pd.to_datetime(bt_input["trade_date"], errors="coerce").dt.date.astype(str)
            bt_input = bt_input.merge(labels, on=["trade_date", "ticker"], how="left")
            backtest = run_technical_setup_backtest(bt_input, horizons=horizons or [1, 3, 5, 10])
        else:
            backtest = pd.DataFrame()
        summary = summarize_technical_backtest(backtest) if with_backtest else pd.DataFrame()
    finished = _now()
    paths = _write_csv(features, setup_signals, backtest if with_backtest else None) if write_csv else {}
    run_id = None
    if save_db and not dry_run:
        with sqlite3.connect(db) as con:
            _save_features(con, features, started)
            _save_setups(con, setup_signals, started)
            if with_backtest:
                run_id = _save_backtest(con, backtest, summary, started, finished, ",".join(setups or []), start, end)
            con.commit()
    print("\nTECHNICAL ANALYSIS SCANNER")
    print(f"Ativos analisados: {features['ticker'].nunique() if not features.empty else 0}")
    print(f"Features geradas: {len(features)}")
    print(f"Setups detectados: {len(setup_signals)}")
    if with_backtest:
        print(f"Backtest tecnico: {len(backtest)} sinais")
        if not summary.empty:
            print(f"Retorno medio D+5: {summary.iloc[0].get('mean_return_5d')}%")
            print(f"Hit rate D+5: {summary.iloc[0].get('hit_rate_5d')}%")
    for name, path in paths.items():
        print(f"CSV {name}: {path}")
    return {"features": features, "setups": setup_signals, "backtest": backtest, "summary": summary, "run_id": run_id, "csv_paths": paths}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scanner opcional de analise tecnica quantitativa.")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--tickers", nargs="*", default=None)
    parser.add_argument("--setups", nargs="*", default=None)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--csv", action="store_true", dest="write_csv")
    parser.add_argument("--with-backtest", action="store_true")
    parser.add_argument("--horizons", nargs="*", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(**vars(args))


if __name__ == "__main__":
    main()
