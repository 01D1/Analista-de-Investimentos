"""Leitura segura de dados para a Mesa Quant Streamlit."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd


BACKTEST_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "tickers_count",
    "signals_count",
    "horizons",
    "mean_return_1d",
    "mean_return_3d",
    "mean_return_5d",
    "mean_return_10d",
    "hit_rate_1d",
    "hit_rate_3d",
    "hit_rate_5d",
    "hit_rate_10d",
    "net_mode",
    "cost_bps",
    "slippage_bps",
    "min_volume",
    "only_tradeable",
    "mean_net_return_1d",
    "mean_net_return_3d",
    "mean_net_return_5d",
    "mean_net_return_10d",
    "net_hit_rate_1d",
    "net_hit_rate_3d",
    "net_hit_rate_5d",
    "net_hit_rate_10d",
    "metadata_json",
]

BACKTEST_RESULT_COLUMNS = [
    "id",
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
    "has_event",
    "event_type",
    "event_impact_score",
    "event_context_type",
    "days_from_event",
    "event_title",
    "impact_direction",
    "explanation",
    "market_regime",
    "metadata_json",
]

QUALITY_FILTER_RUN_COLUMNS = [
    "id",
    "created_at",
    "source_backtest_run_id",
    "filters_json",
    "signals_before",
    "signals_after",
    "removed_pct",
    "mean_net_return_before",
    "mean_net_return_after",
    "hit_rate_before",
    "hit_rate_after",
    "best_signal_type",
    "metadata_json",
]

THRESHOLD_OPTIMIZATION_RUN_COLUMNS = [
    "id",
    "created_at",
    "source_backtest_run_id",
    "param_grid_json",
    "best_params_json",
    "best_mean_net_return",
    "best_hit_rate",
    "best_samples",
    "overfitting_warning",
    "metadata_json",
]

FILTER_WALK_FORWARD_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "objective",
    "windows_count",
    "positive_windows_pct",
    "mean_test_net_return",
    "mean_test_hit_rate",
    "avg_test_signals",
    "avg_top_3_concentration_pct",
    "robustness_class",
    "overfitting_alert",
    "metadata_json",
]

FILTER_WALK_FORWARD_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_params_json",
    "train_signals",
    "test_signals",
    "train_mean_net_return",
    "test_mean_net_return",
    "train_hit_rate",
    "test_hit_rate",
    "top_asset_concentration_pct",
    "top_3_assets_concentration_pct",
    "positive_test_window",
    "overfitting_flag",
    "sample_warning",
    "concentration_warning",
    "metadata_json",
]

GOVERNANCE_REVIEW_COLUMNS = [
    "id",
    "created_at",
    "source_type",
    "source_run_id",
    "candidate_name",
    "governance_status",
    "approved",
    "risk_level",
    "confidence_level",
    "total_signals",
    "windows_count",
    "positive_windows_pct",
    "mean_net_return",
    "mean_hit_rate",
    "avg_top_3_concentration_pct",
    "overfitting_alert",
    "sample_warning",
    "concentration_warning",
    "liquidity_warning",
    "regime_status",
    "allowed_regimes_json",
    "blocked_regimes_json",
    "event_status",
    "allowed_event_contexts_json",
    "blocked_event_contexts_json",
    "summary_text",
    "reasons_for_json",
    "reasons_against_json",
    "required_actions_json",
    "metadata_json",
]

MARKET_EVENT_COLUMNS = [
    "id",
    "event_date",
    "event_datetime",
    "ticker",
    "related_tickers",
    "company_name",
    "event_type",
    "event_source",
    "event_title",
    "event_summary",
    "event_url",
    "sector",
    "macro_tag",
    "commodity_tag",
    "impact_direction",
    "impact_score",
    "confidence",
    "created_at",
    "metadata_json",
]

SIGNAL_EVENT_LINK_COLUMNS = [
    "id",
    "signal_id",
    "backtest_result_id",
    "ticker",
    "signal_date",
    "event_id",
    "event_date",
    "event_type",
    "event_impact_score",
    "days_from_event",
    "link_type",
    "confidence",
    "metadata_json",
]

EVENT_CONTEXT_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "events_count",
    "signals_linked",
    "tickers_count",
    "source",
    "metadata_json",
]

EVENT_COVERAGE_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "sources",
    "events_loaded",
    "events_after_dedup",
    "tickers_count",
    "signals_count",
    "signals_with_event_pct",
    "tickers_with_event_pct",
    "coverage_quality",
    "metadata_json",
]

EVENT_COVERAGE_BY_REGIME_COLUMNS = [
    "id",
    "coverage_run_id",
    "regime_type",
    "regime_value",
    "signals_count",
    "signals_with_event",
    "signals_without_event",
    "signals_with_event_pct",
    "dominant_event_type",
    "dominant_event_source",
    "coverage_quality",
    "metadata_json",
]

SOURCE_HEALTH_CHECK_COLUMNS = [
    "id",
    "checked_at",
    "source_name",
    "status",
    "available",
    "records_count",
    "latest_date",
    "age_days",
    "coverage_hint",
    "path",
    "message",
    "metadata_json",
]

DAILY_ROUTINE_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "sources",
    "health_overall_status",
    "event_coverage_quality",
    "events_loaded",
    "events_after_dedup",
    "signals_covered_pct",
    "governance_status",
    "alerts_count",
    "report_path",
    "metadata_json",
]

OPERATIONAL_ALERT_COLUMNS = [
    "id",
    "created_at",
    "alert_type",
    "severity",
    "title",
    "message",
    "source",
    "resolved",
    "resolved_at",
    "metadata_json",
]

SOURCE_SLA_SNAPSHOT_COLUMNS = [
    "id",
    "created_at",
    "window_days",
    "source_name",
    "total_checks",
    "availability_pct",
    "ok_pct",
    "warning_pct",
    "error_pct",
    "missing_pct",
    "stale_pct",
    "avg_age_days",
    "max_age_days",
    "latest_status",
    "last_ok_at",
    "days_since_last_ok",
    "reliability_class",
    "metadata_json",
]

OBSERVABILITY_SNAPSHOT_COLUMNS = [
    "id",
    "created_at",
    "window_days",
    "overall_status",
    "overall_availability_pct",
    "total_sources",
    "critical_sources",
    "total_alerts",
    "critical_alerts",
    "open_alerts",
    "routine_success_rate_pct",
    "routine_failure_rate_pct",
    "avg_signals_covered_pct",
    "coverage_trend_direction",
    "summary_text",
    "metadata_json",
]

RETENTION_CLEANUP_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "dry_run",
    "status",
    "tables_evaluated",
    "rows_candidates",
    "rows_archived",
    "rows_deleted",
    "archive_dir",
    "warnings_count",
    "errors_count",
    "metadata_json",
]

RETENTION_CLEANUP_DETAIL_COLUMNS = [
    "id",
    "run_id",
    "table_name",
    "cutoff_date",
    "rows_total",
    "rows_to_delete",
    "rows_archived",
    "rows_deleted",
    "protected",
    "status",
    "archive_path",
    "message",
    "metadata_json",
]

MARKET_REGIME_DAILY_COLUMNS = [
    "id",
    "trade_date",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
    "regime_confidence",
    "market_return_mean",
    "market_return_median",
    "pct_assets_positive",
    "total_volume",
    "universe_volatility",
    "metadata_json",
]

REGIME_BACKTEST_SUMMARY_COLUMNS = [
    "id",
    "run_id",
    "regime_type",
    "regime_value",
    "signals_count",
    "mean_gross_return_5d",
    "mean_net_return_5d",
    "hit_rate_5d",
    "tradeable_pct",
    "top_asset_concentration_pct",
    "best_signal_type",
    "best_score_bucket",
    "robustness_class",
    "metadata_json",
]

WALK_FORWARD_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "horizon",
    "windows_count",
    "positive_windows_pct",
    "mean_test_return",
    "mean_test_hit_rate",
    "overfitting_alert",
    "metadata_json",
]

WALK_FORWARD_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_train_signal_type",
    "test_return_best_signal",
    "test_hit_rate_best_signal",
    "best_train_score_bucket",
    "test_return_best_bucket",
    "test_hit_rate_best_bucket",
    "degradation_score",
    "overfitting_flag",
    "metadata_json",
]

CALIBRATION_RUN_COLUMNS = [
    "id",
    "created_at",
    "source",
    "total_assets",
    "mean_score_final",
    "median_score_final",
    "std_score_final",
    "min_score_final",
    "max_score_final",
    "p10_score_final",
    "p25_score_final",
    "p50_score_final",
    "p75_score_final",
    "p90_score_final",
    "count_0_20",
    "count_20_40",
    "count_40_60",
    "count_60_80",
    "count_80_100",
    "inflation_alert",
    "inflation_message",
    "metadata_json",
]

CALIBRATION_ASSET_COLUMNS = [
    "id",
    "run_id",
    "captured_at",
    "asset",
    "legacy_score",
    "score_final",
    "score_momentum",
    "score_tendencia",
    "score_liquidez",
    "score_volatilidade",
    "score_risco",
    "legacy_signal",
    "signal_type",
    "signal_confidence",
    "divergence_type",
    "ranking_legacy",
    "ranking_new",
    "ranking_change",
    "explanation",
    "metadata_json",
]

COMPONENTS = [
    "score_momentum",
    "score_tendencia",
    "score_liquidez",
    "score_volatilidade",
    "score_risco",
]


def _empty(columns: Iterable[str], message: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(columns=list(columns))
    if message:
        df.attrs["mensagem"] = message
    return df


def _db_exists(db_path: str | Path) -> bool:
    return Path(db_path).exists()


def _table_exists(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE name=? AND type IN ('table', 'view')",
        (table,),
    ).fetchone()
    return row is not None


def _read_table(
    db_path: str | Path,
    table: str,
    columns: list[str],
    *,
    where: str = "",
    params: tuple | list | None = None,
    order_by: str = "",
    limit: int | None = None,
) -> pd.DataFrame:
    if not _db_exists(db_path):
        return _empty(columns, f"Banco nao encontrado: {db_path}")

    try:
        with sqlite3.connect(db_path) as con:
            if not _table_exists(con, table):
                return _empty(columns, f"Tabela ausente: {table}")
            existing = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
            select_cols = [col for col in columns if col in existing]
            if not select_cols:
                return _empty(columns, f"Tabela sem colunas esperadas: {table}")
            sql = f"SELECT {', '.join(select_cols)} FROM {table}"
            if where:
                sql += f" WHERE {where}"
            if order_by:
                sql += f" ORDER BY {order_by}"
            if limit:
                sql += f" LIMIT {int(limit)}"
            df = pd.read_sql_query(sql, con, params=params or [])
    except Exception as exc:
        return _empty(columns, f"Erro ao ler {table}: {exc}")

    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df[columns]


def load_latest_backtest_run(db_path: str | Path) -> pd.DataFrame:
    return _read_table(
        db_path,
        "historical_backtest_runs",
        BACKTEST_RUN_COLUMNS,
        order_by="id DESC",
        limit=1,
    )


def load_backtest_runs(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "historical_backtest_runs",
        BACKTEST_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_backtest_results(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "historical_backtest_results",
        BACKTEST_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="trade_date DESC, ticker",
    )


def load_walk_forward_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "walk_forward_runs",
        WALK_FORWARD_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_walk_forward_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "walk_forward_results",
        WALK_FORWARD_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="window_id",
    )


def load_quality_filter_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "quality_filter_runs",
        QUALITY_FILTER_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_threshold_optimization_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "threshold_optimization_runs",
        THRESHOLD_OPTIMIZATION_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_filter_walk_forward_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "filter_walk_forward_runs",
        FILTER_WALK_FORWARD_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_filter_walk_forward_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "filter_walk_forward_results",
        FILTER_WALK_FORWARD_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="window_id",
    )


def load_governance_reviews_for_dashboard(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read_table(
        db_path,
        "governance_reviews",
        GOVERNANCE_REVIEW_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_governance_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_governance_reviews_for_dashboard(db_path, limit=1000)
    columns = ["governance_status", "reviews", "approved_count", "latest_created_at"]
    if df.empty:
        return _empty(columns)
    rows = []
    for status, group in df.groupby("governance_status", dropna=False):
        rows.append(
            {
                "governance_status": status,
                "reviews": int(len(group)),
                "approved_count": int(pd.to_numeric(group.get("approved"), errors="coerce").fillna(0).sum()),
                "latest_created_at": group["created_at"].max(),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("reviews", ascending=False)


def load_market_regimes_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "market_regime_daily",
        MARKET_REGIME_DAILY_COLUMNS,
        order_by="trade_date DESC",
        limit=limit,
    )


def load_regime_backtest_summary_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "regime_backtest_summary",
        REGIME_BACKTEST_SUMMARY_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_market_events_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "market_events",
        MARKET_EVENT_COLUMNS,
        order_by="event_date DESC, ticker",
        limit=limit,
    )


def load_signal_event_links_for_dashboard(db_path: str | Path, limit: int = 1000) -> pd.DataFrame:
    return _read_table(
        db_path,
        "signal_event_links",
        SIGNAL_EVENT_LINK_COLUMNS,
        order_by="signal_date DESC, ticker",
        limit=limit,
    )


def load_event_context_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "event_context_runs",
        EVENT_CONTEXT_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_event_coverage_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "event_coverage_runs",
        EVENT_COVERAGE_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_event_coverage_by_regime_for_dashboard(db_path: str | Path, coverage_run_id: int | None = None) -> pd.DataFrame:
    where = "coverage_run_id = ?" if coverage_run_id is not None else ""
    params = (int(coverage_run_id),) if coverage_run_id is not None else None
    return _read_table(
        db_path,
        "event_coverage_by_regime",
        EVENT_COVERAGE_BY_REGIME_COLUMNS,
        where=where,
        params=params,
        order_by="coverage_run_id DESC, regime_type, regime_value",
    )


def load_source_health_checks_for_dashboard(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read_table(
        db_path,
        "source_health_checks",
        SOURCE_HEALTH_CHECK_COLUMNS,
        order_by="checked_at DESC, source_name",
        limit=limit,
    )


def load_daily_routine_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "daily_routine_runs",
        DAILY_ROUTINE_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_operational_alerts_for_dashboard(db_path: str | Path, open_only: bool = True, limit: int = 100) -> pd.DataFrame:
    where = "COALESCE(resolved, 0) = 0" if open_only else ""
    return _read_table(
        db_path,
        "operational_alerts",
        OPERATIONAL_ALERT_COLUMNS,
        where=where,
        order_by="id DESC",
        limit=limit,
    )


def load_source_sla_snapshots_for_dashboard(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read_table(
        db_path,
        "source_sla_snapshots",
        SOURCE_SLA_SNAPSHOT_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_observability_snapshots_for_dashboard(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read_table(
        db_path,
        "operational_observability_snapshots",
        OBSERVABILITY_SNAPSHOT_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_retention_cleanup_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "retention_cleanup_runs",
        RETENTION_CLEANUP_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_retention_cleanup_details_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "retention_cleanup_details",
        RETENTION_CLEANUP_DETAIL_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_event_context_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = ["group", "value", "signals", "mean_net_return_5d", "hit_rate_5d"]
    if df.empty or "has_event" not in df.columns:
        return _empty(columns)
    rows = []
    ret = pd.to_numeric(df.get("net_return_5d", df.get("future_return_5d")), errors="coerce")
    for group_col in ["has_event", "event_context_type", "event_type", "impact_direction", "primary_regime"]:
        if group_col not in df.columns:
            continue
        for value, group in df.groupby(group_col, dropna=False):
            idx = group.index
            group_ret = ret.loc[idx]
            rows.append(
                {
                    "group": group_col,
                    "value": value,
                    "signals": int(len(group)),
                    "mean_net_return_5d": round(float(group_ret.mean()), 4) if group_ret.notna().any() else 0.0,
                    "hit_rate_5d": round(float((group_ret.dropna() > 0).mean()), 4) if group_ret.notna().any() else 0.0,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def load_calibration_runs_for_dashboard(db_path: str | Path, limit: int = 100) -> pd.DataFrame:
    return _read_table(
        db_path,
        "score_calibration_runs",
        CALIBRATION_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_calibration_assets_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "score_calibration_assets",
        CALIBRATION_ASSET_COLUMNS,
        where=where,
        params=params,
        order_by="captured_at DESC, asset",
    )


def load_score_distribution_history_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_calibration_runs_for_dashboard(db_path, limit=1000)
    if df.empty:
        return df
    df = df.sort_values("created_at").reset_index(drop=True)
    for col in [
        "mean_score_final",
        "median_score_final",
        "p90_score_final",
        "count_80_100",
        "inflation_alert",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _numeric(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df.get(col), errors="coerce")


def load_signal_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = [
        "signal_type",
        "signals",
        "mean_return_5d",
        "mean_return_10d",
        "hit_rate_5d",
        "hit_rate_10d",
        "best_return_5d",
        "worst_return_5d",
    ]
    if df.empty or "signal_type" not in df.columns:
        return _empty(columns)

    rows = []
    for signal_type, group in df.groupby("signal_type", dropna=False):
        ret5 = _numeric(group, "future_return_5d")
        ret10 = _numeric(group, "future_return_10d")
        rows.append(
            {
                "signal_type": signal_type,
                "signals": int(len(group)),
                "mean_return_5d": round(float(ret5.mean()), 4) if ret5.notna().any() else 0.0,
                "mean_return_10d": round(float(ret10.mean()), 4) if ret10.notna().any() else 0.0,
                "hit_rate_5d": round(float((ret5 > 0).mean()), 4) if ret5.notna().any() else 0.0,
                "hit_rate_10d": round(float((ret10 > 0).mean()), 4) if ret10.notna().any() else 0.0,
                "best_return_5d": round(float(ret5.max()), 4) if ret5.notna().any() else 0.0,
                "worst_return_5d": round(float(ret5.min()), 4) if ret5.notna().any() else 0.0,
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("mean_return_10d", ascending=False)


def load_score_bucket_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = [
        "score_bucket",
        "signals",
        "mean_return_5d",
        "mean_return_10d",
        "hit_rate_5d",
        "hit_rate_10d",
    ]
    if df.empty or "score_bucket" not in df.columns:
        return _empty(columns)

    rows = []
    for bucket, group in df.groupby("score_bucket", dropna=False):
        ret5 = _numeric(group, "future_return_5d")
        ret10 = _numeric(group, "future_return_10d")
        rows.append(
            {
                "score_bucket": bucket,
                "signals": int(len(group)),
                "mean_return_5d": round(float(ret5.mean()), 4) if ret5.notna().any() else 0.0,
                "mean_return_10d": round(float(ret10.mean()), 4) if ret10.notna().any() else 0.0,
                "hit_rate_5d": round(float((ret5 > 0).mean()), 4) if ret5.notna().any() else 0.0,
                "hit_rate_10d": round(float((ret10 > 0).mean()), 4) if ret10.notna().any() else 0.0,
            }
        )
    order = {"0_20": 0, "20_40": 1, "40_60": 2, "60_80": 3, "80_100": 4}
    out = pd.DataFrame(rows, columns=columns)
    out["_order"] = out["score_bucket"].map(order).fillna(99)
    return out.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def load_net_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = [
        "signals",
        "tradeable_signals",
        "untradeable_signals",
        "gross_mean_return_5d",
        "net_mean_return_5d",
        "cost_impact_5d",
        "gross_hit_rate_5d",
        "net_hit_rate_5d",
    ]
    if df.empty:
        return _empty(columns)
    gross = _numeric(df, "future_return_5d")
    net = _numeric(df, "net_return_5d")
    tradeable = pd.to_numeric(df.get("is_tradeable"), errors="coerce")
    row = {
        "signals": int(len(df)),
        "tradeable_signals": int(tradeable.fillna(0).sum()) if "is_tradeable" in df.columns else 0,
        "untradeable_signals": int((tradeable == 0).sum()) if "is_tradeable" in df.columns else 0,
        "gross_mean_return_5d": round(float(gross.mean()), 4) if gross.notna().any() else 0.0,
        "net_mean_return_5d": round(float(net.mean()), 4) if net.notna().any() else 0.0,
        "gross_hit_rate_5d": round(float((gross.dropna() > 0).mean()), 4) if gross.notna().any() else 0.0,
        "net_hit_rate_5d": round(float((net.dropna() > 0).mean()), 4) if net.notna().any() else 0.0,
    }
    row["cost_impact_5d"] = round(row["gross_mean_return_5d"] - row["net_mean_return_5d"], 4)
    return pd.DataFrame([row], columns=columns)


def load_execution_quality_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = ["execution_quality", "signals", "mean_net_return_5d", "hit_rate_net_5d", "tradeable_signals"]
    if df.empty or "execution_quality" not in df.columns:
        return _empty(columns)
    rows = []
    for quality, group in df.groupby("execution_quality", dropna=False):
        net = _numeric(group, "net_return_5d")
        tradeable = pd.to_numeric(group.get("is_tradeable"), errors="coerce")
        rows.append(
            {
                "execution_quality": quality,
                "signals": int(len(group)),
                "mean_net_return_5d": round(float(net.mean()), 4) if net.notna().any() else 0.0,
                "hit_rate_net_5d": round(float((net.dropna() > 0).mean()), 4) if net.notna().any() else 0.0,
                "tradeable_signals": int(tradeable.fillna(0).sum()) if "is_tradeable" in group.columns else 0,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def load_capacity_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    df = load_backtest_results(db_path)
    columns = ["group", "value", "signals", "mean_capacity", "mean_net_return_5d", "hit_rate_net_5d"]
    if df.empty or "estimated_capacity" not in df.columns:
        return _empty(columns)
    rows = []
    for group_col in ["signal_type", "score_bucket", "capacity_class", "signal_quality"]:
        if group_col not in df.columns:
            continue
        for value, group in df.groupby(group_col, dropna=False):
            capacity = _numeric(group, "estimated_capacity")
            net = _numeric(group, "net_return_5d")
            rows.append(
                {
                    "group": group_col,
                    "value": value,
                    "signals": int(len(group)),
                    "mean_capacity": round(float(capacity.mean()), 2) if capacity.notna().any() else 0.0,
                    "mean_net_return_5d": round(float(net.mean()), 4) if net.notna().any() else 0.0,
                    "hit_rate_net_5d": round(float((net.dropna() > 0).mean()), 4) if net.notna().any() else 0.0,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def load_component_summary_for_dashboard(db_path: str | Path) -> pd.DataFrame:
    assets = load_backtest_results(db_path)
    if assets.empty or not any(component in assets.columns and pd.to_numeric(assets[component], errors="coerce").notna().any() for component in COMPONENTS):
        assets = load_calibration_assets_for_dashboard(db_path)
    columns = ["component", "mean", "median", "min", "max", "std", "sample_size"]
    if assets.empty:
        return _empty(columns)

    rows = []
    for component in COMPONENTS:
        if component not in assets.columns:
            continue
        values = pd.to_numeric(assets[component], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "component": component,
                "mean": round(float(values.mean()), 4),
                "median": round(float(values.median()), 4),
                "min": round(float(values.min()), 4),
                "max": round(float(values.max()), 4),
                "std": round(float(values.std(ddof=0)), 4),
                "sample_size": int(len(values)),
            }
        )
    return pd.DataFrame(rows, columns=columns)
