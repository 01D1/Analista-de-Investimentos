"""CLI para backtest historico do score quantitativo com COTAHIST."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.db.init_db import init_database
from src.quant.historical_backtest import (
    generate_historical_backtest_report,
    run_historical_backtest,
    summarize_backtest_by_score_bucket,
    summarize_backtest_by_signal_type,
)
from src.quant.historical_loader import load_daily_prices
from src.quant.historical_signals import generate_historical_features, generate_historical_scores
from src.quant.market_regimes import assign_regimes_to_backtest, build_market_proxy_from_universe, calculate_market_regime_features
from src.context.event_importer import load_events_from_db
from src.quant.event_backtest import generate_event_context_report, summarize_backtest_by_event_context
from src.quant.event_linker import link_events_to_signals
from src.quant.net_backtest import (
    apply_execution_costs_to_backtest,
    generate_net_backtest_report,
    summarize_by_execution_quality,
    summarize_net_vs_gross,
)
from src.quant.capacity import classify_capacity, estimate_trade_capacity
from src.quant.regime_backtest import summarize_backtest_by_regime
from src.quant.score_calibration import evaluate_score_predictiveness, suggest_weight_adjustments
from src.quant.signal_filters import (
    apply_quality_filters,
    generate_quality_filter_report,
    summarize_filter_impact,
)
from src.quant.threshold_optimizer import (
    DEFAULT_PARAM_GRID,
    generate_threshold_report,
    grid_search_thresholds,
    rank_threshold_results,
)
from src.utils import load_config, project_path


def _parse_horizons(value: str | None) -> list[int]:
    if not value:
        return [1, 3, 5, 10]
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _write_csvs(
    *,
    backtest_df: pd.DataFrame,
    summary_signal: pd.DataFrame,
    summary_bucket: pd.DataFrame,
    reports_dir: Path,
    net_summary: pd.DataFrame | None = None,
    filter_impact: pd.DataFrame | None = None,
    threshold_results: pd.DataFrame | None = None,
    regime_summary: pd.DataFrame | None = None,
    event_summary: pd.DataFrame | None = None,
) -> dict[str, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "results": reports_dir / f"historical_backtest_results_{stamp}.csv",
        "signals": reports_dir / f"historical_backtest_by_signal_{stamp}.csv",
        "buckets": reports_dir / f"historical_backtest_by_bucket_{stamp}.csv",
    }
    backtest_df.to_csv(paths["results"], index=False, sep=";", decimal=",")
    summary_signal.to_csv(paths["signals"], index=False, sep=";", decimal=",")
    summary_bucket.to_csv(paths["buckets"], index=False, sep=";", decimal=",")
    if net_summary is not None and not net_summary.empty:
        paths["net_results"] = reports_dir / f"historical_backtest_net_results_{stamp}.csv"
        paths["net_summary"] = reports_dir / f"historical_backtest_net_summary_{stamp}.csv"
        backtest_df.to_csv(paths["net_results"], index=False, sep=";", decimal=",")
        net_summary.to_csv(paths["net_summary"], index=False, sep=";", decimal=",")
    if filter_impact is not None and not filter_impact.empty:
        paths["filter_impact"] = reports_dir / f"filter_impact_{stamp}.csv"
        filter_impact.to_csv(paths["filter_impact"], index=False, sep=";", decimal=",")
    if threshold_results is not None and not threshold_results.empty:
        paths["threshold_optimization"] = reports_dir / f"threshold_optimization_{stamp}.csv"
        threshold_results.to_csv(paths["threshold_optimization"], index=False, sep=";", decimal=",")
    if regime_summary is not None and not regime_summary.empty:
        paths["regimes"] = reports_dir / f"historical_backtest_by_regime_{stamp}.csv"
        regime_summary.to_csv(paths["regimes"], index=False, sep=";", decimal=",")
    if event_summary is not None and not event_summary.empty:
        paths["events"] = reports_dir / f"historical_backtest_by_event_context_{stamp}.csv"
        event_summary.to_csv(paths["events"], index=False, sep=";", decimal=",")
    return paths


def _column_mean(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns:
        return None
    value = pd.to_numeric(df[col], errors="coerce").mean()
    return None if pd.isna(value) else round(float(value), 4)


def _save_backtest_run(
    *,
    db_path: Path,
    backtest_df: pd.DataFrame,
    start_date: str | None,
    end_date: str | None,
    horizons: list[int],
    metadata: dict,
    net_mode: bool = False,
    cost_bps: float | None = None,
    slippage_bps: float | None = None,
    min_volume: float | None = None,
    only_tradeable: bool = False,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO historical_backtest_runs (
                created_at, start_date, end_date, tickers_count, signals_count, horizons,
                mean_return_1d, mean_return_3d, mean_return_5d, mean_return_10d,
                hit_rate_1d, hit_rate_3d, hit_rate_5d, hit_rate_10d,
                net_mode, cost_bps, slippage_bps, min_volume, only_tradeable,
                mean_net_return_1d, mean_net_return_3d, mean_net_return_5d, mean_net_return_10d,
                net_hit_rate_1d, net_hit_rate_3d, net_hit_rate_5d, net_hit_rate_10d,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                start_date,
                end_date,
                int(backtest_df["ticker"].nunique()) if "ticker" in backtest_df else 0,
                int(len(backtest_df)),
                ",".join(str(h) for h in horizons),
                _column_mean(backtest_df, "future_return_1d"),
                _column_mean(backtest_df, "future_return_3d"),
                _column_mean(backtest_df, "future_return_5d"),
                _column_mean(backtest_df, "future_return_10d"),
                _column_mean(backtest_df, "hit_1d"),
                _column_mean(backtest_df, "hit_3d"),
                _column_mean(backtest_df, "hit_5d"),
                _column_mean(backtest_df, "hit_10d"),
                int(bool(net_mode)),
                cost_bps,
                slippage_bps,
                min_volume,
                int(bool(only_tradeable)),
                _column_mean(backtest_df, "net_return_1d"),
                _column_mean(backtest_df, "net_return_3d"),
                _column_mean(backtest_df, "net_return_5d"),
                _column_mean(backtest_df, "net_return_10d"),
                _column_mean((backtest_df.assign(net_hit_1d=pd.to_numeric(backtest_df.get("net_return_1d"), errors="coerce") > 0) if "net_return_1d" in backtest_df else backtest_df), "net_hit_1d"),
                _column_mean((backtest_df.assign(net_hit_3d=pd.to_numeric(backtest_df.get("net_return_3d"), errors="coerce") > 0) if "net_return_3d" in backtest_df else backtest_df), "net_hit_3d"),
                _column_mean((backtest_df.assign(net_hit_5d=pd.to_numeric(backtest_df.get("net_return_5d"), errors="coerce") > 0) if "net_return_5d" in backtest_df else backtest_df), "net_hit_5d"),
                _column_mean((backtest_df.assign(net_hit_10d=pd.to_numeric(backtest_df.get("net_return_10d"), errors="coerce") > 0) if "net_return_10d" in backtest_df else backtest_df), "net_hit_10d"),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        run_id = int(cur.lastrowid)

        result_cols = [
            "trade_date",
            "ticker",
            "score_final",
            "score_momentum",
            "score_tendencia",
            "score_liquidez",
            "score_volatilidade",
            "score_risco",
            "signal_type",
            "signal_confidence",
            "explanation",
            "market_regime",
            "future_return_1d",
            "future_return_3d",
            "future_return_5d",
            "future_return_10d",
            "net_return_1d",
            "net_return_3d",
            "net_return_5d",
            "net_return_10d",
            "max_favorable_excursion_5d",
            "max_adverse_excursion_5d",
            "score_bucket",
            "execution_quality",
            "liquidity_penalty",
            "total_cost_pct",
            "total_slippage_pct",
            "is_tradeable",
            "volume",
            "trades",
            "signal_quality",
            "estimated_capacity",
            "capacity_class",
            "primary_regime",
            "trend_regime",
            "volatility_regime",
            "liquidity_regime",
            "risk_regime",
            "regime_confidence",
            "has_event",
            "event_type",
            "event_impact_score",
            "event_context_type",
            "days_from_event",
            "event_title",
            "impact_direction",
        ]
        db_result_cols = [
            "run_id",
            "trade_date",
            "ticker",
            "score_final",
            "score_momentum",
            "score_tendencia",
            "score_liquidez",
            "score_volatilidade",
            "score_risco",
            "signal_type",
            "signal_confidence",
            "future_return_1d",
            "future_return_3d",
            "future_return_5d",
            "future_return_10d",
            "net_return_1d",
            "net_return_3d",
            "net_return_5d",
            "net_return_10d",
            "mfe_5d",
            "mae_5d",
            "score_bucket",
            "execution_quality",
            "liquidity_penalty",
            "total_cost_pct",
            "total_slippage_pct",
            "is_tradeable",
            "volume",
            "trades",
            "signal_quality",
            "estimated_capacity",
            "capacity_class",
            "primary_regime",
            "trend_regime",
            "volatility_regime",
            "liquidity_regime",
            "risk_regime",
            "regime_confidence",
            "explanation",
            "market_regime",
            "has_event",
            "event_type",
            "event_impact_score",
            "event_context_type",
            "days_from_event",
            "event_title",
            "impact_direction",
            "metadata_json",
        ]
        source_alias = {
            "mfe_5d": "max_favorable_excursion_5d",
            "mae_5d": "max_adverse_excursion_5d",
        }
        placeholders = ", ".join(["?"] * len(db_result_cols))
        sql = f"INSERT INTO historical_backtest_results ({', '.join(db_result_cols)}) VALUES ({placeholders})"
        for _, row in backtest_df.iterrows():
            values = []
            for col in db_result_cols:
                if col == "run_id":
                    values.append(run_id)
                elif col == "metadata_json":
                    values.append(json.dumps({k: row.get(k) for k in result_cols if k in row.index}, ensure_ascii=False, default=str))
                elif col == "is_tradeable":
                    values.append(int(bool(row.get("is_tradeable"))) if "is_tradeable" in row.index and pd.notna(row.get("is_tradeable")) else None)
                elif col == "has_event":
                    values.append(int(bool(row.get("has_event"))) if "has_event" in row.index and pd.notna(row.get("has_event")) else None)
                else:
                    values.append(row.get(source_alias.get(col, col)))
            cur.execute(sql, values)
        con.commit()
    return run_id


def _annotate_capacity(backtest_df: pd.DataFrame, capital: float = 100_000.0, desired_allocation: float = 10_000.0) -> pd.DataFrame:
    if backtest_df is None or backtest_df.empty:
        return backtest_df
    df = backtest_df.copy()
    if "volume" not in df.columns:
        return df
    df["estimated_capacity"] = df["volume"].apply(lambda volume: estimate_trade_capacity(volume, participation_rate=0.01))
    df["capacity_class"] = df["volume"].apply(
        lambda volume: classify_capacity(volume, capital=capital, desired_allocation=desired_allocation)
    )
    return df


def _save_quality_filter_run(
    *,
    db_path: Path,
    summary: dict,
    filters: dict,
    source_backtest_run_id: int | None = None,
) -> int:
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO quality_filter_runs (
                created_at, source_backtest_run_id, filters_json, signals_before, signals_after,
                removed_pct, mean_net_return_before, mean_net_return_after,
                hit_rate_before, hit_rate_after, best_signal_type, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                source_backtest_run_id,
                json.dumps(filters, ensure_ascii=False, default=str),
                summary.get("signals_before"),
                summary.get("signals_after"),
                summary.get("removed_pct"),
                summary.get("mean_net_return_before"),
                summary.get("mean_net_return_after"),
                summary.get("hit_rate_before"),
                summary.get("hit_rate_after"),
                summary.get("best_signal_type_after"),
                json.dumps(summary, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def _save_threshold_optimization_run(
    *,
    db_path: Path,
    ranked_results: pd.DataFrame,
    param_grid: dict,
    source_backtest_run_id: int | None = None,
) -> int | None:
    if ranked_results is None or ranked_results.empty:
        return None
    best = ranked_results.iloc[0].to_dict()
    warning = "amostra_insuficiente" if not bool(best.get("sample_ok", False)) else ""
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO threshold_optimization_runs (
                created_at, source_backtest_run_id, param_grid_json, best_params_json,
                best_mean_net_return, best_hit_rate, best_samples, overfitting_warning, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                source_backtest_run_id,
                json.dumps(param_grid, ensure_ascii=False, default=str),
                json.dumps(best.get("params", {}), ensure_ascii=False, default=str),
                best.get("mean_net_return_5d"),
                best.get("hit_rate_net_5d"),
                best.get("samples"),
                warning,
                json.dumps(best, ensure_ascii=False, default=str),
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def _save_regime_summary(db_path: Path, run_id: int, regime_summary: pd.DataFrame) -> None:
    if regime_summary is None or regime_summary.empty:
        return
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        for _, row in regime_summary.iterrows():
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


def run(
    *,
    start: str | None = None,
    end: str | None = None,
    tickers: list[str] | None = None,
    horizons: list[int] | None = None,
    top: int = 20,
    min_samples: int = 5,
    write_csv: bool = False,
    save_db: bool = False,
    net: bool = False,
    cost_bps: float = 10.0,
    slippage_bps: float = 5.0,
    min_volume: float = 5_000_000,
    only_tradeable: bool = False,
    quality_filter: bool = False,
    min_score_final: float | None = None,
    min_confidence: float | None = None,
    min_liquidity_score: float | None = None,
    min_risk_score: float | None = None,
    min_execution_quality: str | None = None,
    allowed_signal_types: list[str] | None = None,
    optimize_thresholds: bool = False,
    with_regimes: bool = False,
    regime_source: str = "universe",
    benchmark: str = "IBOV",
    with_events: bool = False,
    event_window_before: int = 1,
    event_window_after: int = 1,
) -> dict:
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    horizons = horizons or [1, 3, 5, 10]

    prices = load_daily_prices(db_path, tickers=tickers, start_date=start, end_date=end)
    if prices.empty:
        message = prices.attrs.get("mensagem", "Sem precos historicos disponiveis.")
        print(message)
        return {"prices": prices, "backtest": pd.DataFrame(), "message": message}

    features = generate_historical_features(prices)
    scored = generate_historical_scores(features)
    backtest = run_historical_backtest(scored, horizons=horizons)
    if backtest.empty:
        message = "Precos carregados, mas nao houve janela futura suficiente para backtest."
        print(message)
        return {"prices": prices, "features": features, "scores": scored, "backtest": backtest, "message": message}

    regime_summary = pd.DataFrame()
    regimes = pd.DataFrame()
    if with_regimes:
        market_source = prices
        if regime_source == "benchmark":
            bench_prices = load_daily_prices(db_path, tickers=[benchmark], start_date=start, end_date=end)
            if not bench_prices.empty:
                market_source = bench_prices
        proxy = build_market_proxy_from_universe(market_source)
        regimes = calculate_market_regime_features(proxy)
        backtest = assign_regimes_to_backtest(backtest, regimes)

    event_summary = pd.DataFrame()
    events = pd.DataFrame()
    if with_events:
        events = load_events_from_db(db_path, start_date=start, end_date=end)
        backtest = link_events_to_signals(
            backtest,
            events,
            window_days_before=event_window_before,
            window_days_after=event_window_after,
        )

    backtest = _annotate_capacity(backtest)
    net_summary_dict = {}
    quality_summary = pd.DataFrame()
    if net:
        backtest = apply_execution_costs_to_backtest(
            backtest,
            cost_bps=cost_bps,
            slippage_bps=slippage_bps,
            min_volume=min_volume,
            only_tradeable=only_tradeable,
        )
        net_summary_dict = summarize_net_vs_gross(backtest)
        quality_summary = summarize_by_execution_quality(backtest)

    filter_summary: dict = {}
    filter_impact_df = pd.DataFrame()
    threshold_results = pd.DataFrame()
    ranked_thresholds = pd.DataFrame()
    quality_filter_config = {
        "min_score_final": min_score_final if min_score_final is not None else 0,
        "min_confidence": min_confidence if min_confidence is not None else 0,
        "min_liquidity_score": min_liquidity_score if min_liquidity_score is not None else 0,
        "min_risk_score": min_risk_score if min_risk_score is not None else 0,
        "min_execution_quality": min_execution_quality,
        "min_volume": min_volume if net else 0,
        "only_tradeable": only_tradeable,
        "remove_inviavel": True,
        "remove_ruim": min_execution_quality is not None and min_execution_quality.upper() in {"ACEITAVEL", "ACEITÁVEL", "BOA", "EXCELENTE"},
        "allowed_signal_types": allowed_signal_types,
    }
    if quality_filter:
        before_filter = backtest.copy()
        backtest = apply_quality_filters(backtest, quality_filter_config)
        filter_summary = summarize_filter_impact(before_filter, backtest)
        filter_impact_df = pd.DataFrame([filter_summary])
        if net:
            net_summary_dict = summarize_net_vs_gross(backtest)
            quality_summary = summarize_by_execution_quality(backtest)
        print("\nFILTROS DE QUALIDADE")
        print(generate_quality_filter_report(filter_summary))

    if optimize_thresholds:
        threshold_results = grid_search_thresholds(
            backtest,
            DEFAULT_PARAM_GRID,
            objective="mean_net_return_5d",
            min_samples=min_samples,
        )
        ranked_thresholds = rank_threshold_results(threshold_results)
        print("\nOTIMIZAÇÃO DE THRESHOLDS")
        print(generate_threshold_report(ranked_thresholds))

    if with_regimes:
        regime_summary = summarize_backtest_by_regime(backtest)
    if with_events:
        event_summary = summarize_backtest_by_event_context(backtest)

    summary_signal = summarize_backtest_by_signal_type(backtest, min_samples=min_samples)
    summary_bucket = summarize_backtest_by_score_bucket(backtest, min_samples=min_samples)
    evaluation = evaluate_score_predictiveness(backtest)
    suggestion = suggest_weight_adjustments(evaluation)
    report = generate_historical_backtest_report(summary_signal, summary_bucket, suggestion)

    print("\nBACKTEST HISTORICO DO SCORE QUANTITATIVO")
    print(report)
    print("\nResumo por tipo de sinal:")
    print(summary_signal.head(top).to_string(index=False))
    print("\nResumo por faixa de score_final:")
    print(summary_bucket.head(top).to_string(index=False))
    if net:
        print("\nBACKTEST LÍQUIDO")
        print(generate_net_backtest_report(net_summary_dict, net_summary_dict))
        if not quality_summary.empty:
            print("\nResumo por qualidade de execução:")
            print(quality_summary.to_string(index=False))
    if with_events:
        print("\nCONTEXTO DE EVENTOS")
        print(generate_event_context_report(event_summary))
        if not event_summary.empty:
            print(event_summary.head(top).to_string(index=False))

    paths = {}
    if write_csv:
        paths = _write_csvs(
            backtest_df=backtest,
            summary_signal=summary_signal,
            summary_bucket=summary_bucket,
            reports_dir=project_path("data/reports"),
            net_summary=quality_summary if net else None,
            filter_impact=filter_impact_df if quality_filter else None,
            threshold_results=ranked_thresholds if optimize_thresholds else None,
            regime_summary=regime_summary if with_regimes else None,
            event_summary=event_summary if with_events else None,
        )
        print("\nCSVs gerados:")
        for name, path in paths.items():
            print(f"- {name}: {path}")

    run_id = None
    if save_db:
        run_id = _save_backtest_run(
            db_path=db_path,
            backtest_df=backtest,
            start_date=start,
            end_date=end,
            horizons=horizons,
            metadata={
                "tickers": tickers,
                "min_samples": min_samples,
                "net": net,
                "cost_bps": cost_bps,
                "slippage_bps": slippage_bps,
                "min_volume": min_volume,
                "only_tradeable": only_tradeable,
                "quality_filter": quality_filter,
                "quality_filter_config": quality_filter_config if quality_filter else None,
                "optimize_thresholds": optimize_thresholds,
                "with_regimes": with_regimes,
                "regime_source": regime_source,
                "benchmark": benchmark,
                "with_events": with_events,
                "event_window_before": event_window_before,
                "event_window_after": event_window_after,
            },
            net_mode=net,
            cost_bps=cost_bps if net else None,
            slippage_bps=slippage_bps if net else None,
            min_volume=min_volume if net else None,
            only_tradeable=only_tradeable,
        )
        print(f"\nBacktest historico salvo no banco. run_id={run_id}")
        if with_regimes and not regime_summary.empty:
            _save_regime_summary(db_path, run_id, regime_summary)
            print("Resumo por regimes salvo no banco.")
        if quality_filter and filter_summary:
            quality_run_id = _save_quality_filter_run(
                db_path=db_path,
                summary=filter_summary,
                filters=quality_filter_config,
                source_backtest_run_id=run_id,
            )
            print(f"Rodada de filtros salva no banco. quality_filter_run_id={quality_run_id}")
        if optimize_thresholds and not ranked_thresholds.empty:
            threshold_run_id = _save_threshold_optimization_run(
                db_path=db_path,
                ranked_results=ranked_thresholds,
                param_grid=DEFAULT_PARAM_GRID,
                source_backtest_run_id=run_id,
            )
            print(f"Otimização de thresholds salva no banco. threshold_optimization_run_id={threshold_run_id}")

    return {
        "prices": prices,
        "features": features,
        "scores": scored,
        "backtest": backtest,
        "summary_signal": summary_signal,
        "summary_bucket": summary_bucket,
        "evaluation": evaluation,
        "suggestion": suggestion,
        "net_summary": net_summary_dict,
        "quality_summary": quality_summary,
        "filter_summary": filter_summary,
        "threshold_results": ranked_thresholds,
        "regimes": regimes,
        "regime_summary": regime_summary,
        "events": events,
        "event_summary": event_summary,
        "csv_paths": paths,
        "run_id": run_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest historico do score quantitativo usando COTAHIST no SQLite.")
    parser.add_argument("--start", default=None, help="Data inicial no formato YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Data final no formato YYYY-MM-DD.")
    parser.add_argument("--tickers", nargs="*", default=None, help="Lista opcional de tickers.")
    parser.add_argument("--horizons", default="1,3,5,10", help="Horizontes separados por virgula, exemplo: 1,3,5,10.")
    parser.add_argument("--top", type=int, default=20, help="Quantidade de linhas por resumo.")
    parser.add_argument("--min-samples", type=int, default=5, help="Amostra minima para marcar grupo como suficiente.")
    parser.add_argument("--csv", action="store_true", help="Salva resultados e resumos em data/reports.")
    parser.add_argument("--save-db", action="store_true", help="Salva resultados agregados e linhas do backtest no SQLite.")
    parser.add_argument("--net", action="store_true", help="Calcula retornos líquidos com custos, slippage e liquidez.")
    parser.add_argument("--cost-bps", type=float, default=10.0, help="Custo total estimado por ponta em basis points.")
    parser.add_argument("--slippage-bps", type=float, default=5.0, help="Slippage estimado por ponta em basis points.")
    parser.add_argument("--min-volume", type=float, default=5_000_000, help="Volume financeiro mínimo para considerar sinal negociável.")
    parser.add_argument("--only-tradeable", action="store_true", help="Remove sinais RUIM/INVIAVEL ou abaixo da liquidez mínima no modo líquido.")
    parser.add_argument("--quality-filter", action="store_true", help="Aplica filtros opcionais de qualidade após o backtest.")
    parser.add_argument("--min-score-final", type=float, default=None, help="Score_final mínimo para o filtro de qualidade.")
    parser.add_argument("--min-confidence", type=float, default=None, help="Confiança mínima do sinal, entre 0 e 1.")
    parser.add_argument("--min-liquidity-score", type=float, default=None, help="Score de liquidez mínimo.")
    parser.add_argument("--min-risk-score", type=float, default=None, help="Score de risco mínimo. Maior significa risco mais aceitável.")
    parser.add_argument("--min-execution-quality", default=None, help="Qualidade mínima de execução: ACEITAVEL, BOA ou EXCELENTE.")
    parser.add_argument("--allowed-signal-types", nargs="*", default=None, help="Lista opcional de signal_type aceitos.")
    parser.add_argument("--optimize-thresholds", action="store_true", help="Testa combinações de thresholds sem aplicar automaticamente ao scanner.")
    parser.add_argument("--with-regimes", action="store_true", help="Calcula regimes de mercado e adiciona ao backtest.")
    parser.add_argument("--regime-source", choices=["universe", "benchmark"], default="universe", help="Fonte dos regimes.")
    parser.add_argument("--benchmark", default="IBOV", help="Ticker de benchmark quando --regime-source benchmark.")
    parser.add_argument("--with-events", action="store_true", help="Carrega market_events e marca contexto de eventos nos sinais.")
    parser.add_argument("--event-window-before", type=int, default=1, help="Dias antes do sinal aceitos para vincular evento.")
    parser.add_argument("--event-window-after", type=int, default=1, help="Dias depois do sinal aceitos para vincular evento.")
    args = parser.parse_args()

    run(
        start=args.start,
        end=args.end,
        tickers=args.tickers,
        horizons=_parse_horizons(args.horizons),
        top=args.top,
        min_samples=args.min_samples,
        write_csv=args.csv,
        save_db=args.save_db,
        net=args.net,
        cost_bps=args.cost_bps,
        slippage_bps=args.slippage_bps,
        min_volume=args.min_volume,
        only_tradeable=args.only_tradeable,
        quality_filter=args.quality_filter,
        min_score_final=args.min_score_final,
        min_confidence=args.min_confidence,
        min_liquidity_score=args.min_liquidity_score,
        min_risk_score=args.min_risk_score,
        min_execution_quality=args.min_execution_quality,
        allowed_signal_types=args.allowed_signal_types,
        optimize_thresholds=args.optimize_thresholds,
        with_regimes=args.with_regimes,
        regime_source=args.regime_source,
        benchmark=args.benchmark,
        with_events=args.with_events,
        event_window_before=args.event_window_before,
        event_window_after=args.event_window_after,
    )


if __name__ == "__main__":
    main()
