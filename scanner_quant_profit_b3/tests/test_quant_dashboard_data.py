import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.reports.quant_dashboard_data import (
    load_backtest_results,
    load_backtest_runs,
    load_calibration_assets_for_dashboard,
    load_calibration_runs_for_dashboard,
    load_component_summary_for_dashboard,
    load_capacity_summary_for_dashboard,
    load_daily_routine_runs_for_dashboard,
    load_filter_walk_forward_results_for_dashboard,
    load_filter_walk_forward_runs_for_dashboard,
    load_event_context_runs_for_dashboard,
    load_event_context_summary_for_dashboard,
    load_event_coverage_by_regime_for_dashboard,
    load_event_coverage_runs_for_dashboard,
    load_governance_reviews_for_dashboard,
    load_governance_summary_for_dashboard,
    load_market_regimes_for_dashboard,
    load_market_events_for_dashboard,
    load_operational_alerts_for_dashboard,
    load_observability_snapshots_for_dashboard,
    load_regime_backtest_summary_for_dashboard,
    load_retention_cleanup_details_for_dashboard,
    load_retention_cleanup_runs_for_dashboard,
    load_signal_event_links_for_dashboard,
    load_latest_backtest_run,
    load_score_bucket_summary_for_dashboard,
    load_score_distribution_history_for_dashboard,
    load_signal_summary_for_dashboard,
    load_source_health_checks_for_dashboard,
    load_source_sla_snapshots_for_dashboard,
    load_execution_quality_summary_for_dashboard,
    load_net_summary_for_dashboard,
    load_quality_filter_runs_for_dashboard,
    load_walk_forward_results_for_dashboard,
    load_walk_forward_runs_for_dashboard,
    load_threshold_optimization_runs_for_dashboard,
)


def test_dashboard_loaders_handle_missing_database(tmp_path):
    db_path = tmp_path / "missing.db"

    assert load_latest_backtest_run(db_path).empty
    assert load_backtest_runs(db_path).empty
    assert load_backtest_results(db_path).empty
    assert load_calibration_runs_for_dashboard(db_path).empty
    assert load_calibration_assets_for_dashboard(db_path).empty
    assert load_walk_forward_runs_for_dashboard(db_path).empty
    assert load_walk_forward_results_for_dashboard(db_path).empty
    assert load_quality_filter_runs_for_dashboard(db_path).empty
    assert load_threshold_optimization_runs_for_dashboard(db_path).empty
    assert load_filter_walk_forward_runs_for_dashboard(db_path).empty
    assert load_filter_walk_forward_results_for_dashboard(db_path).empty
    assert load_governance_reviews_for_dashboard(db_path).empty
    assert load_governance_summary_for_dashboard(db_path).empty
    assert load_market_regimes_for_dashboard(db_path).empty
    assert load_regime_backtest_summary_for_dashboard(db_path).empty
    assert load_market_events_for_dashboard(db_path).empty
    assert load_signal_event_links_for_dashboard(db_path).empty
    assert load_event_context_runs_for_dashboard(db_path).empty
    assert load_event_coverage_runs_for_dashboard(db_path).empty
    assert load_event_coverage_by_regime_for_dashboard(db_path).empty
    assert load_event_context_summary_for_dashboard(db_path).empty
    assert load_source_health_checks_for_dashboard(db_path).empty
    assert load_daily_routine_runs_for_dashboard(db_path).empty
    assert load_operational_alerts_for_dashboard(db_path).empty
    assert load_source_sla_snapshots_for_dashboard(db_path).empty
    assert load_observability_snapshots_for_dashboard(db_path).empty
    assert load_retention_cleanup_runs_for_dashboard(db_path).empty
    assert load_retention_cleanup_details_for_dashboard(db_path).empty


def test_dashboard_loaders_handle_empty_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)

    runs = load_backtest_runs(db_path)
    results = load_backtest_results(db_path)
    calibration = load_calibration_runs_for_dashboard(db_path)

    assert runs.empty
    assert "signals_count" in runs.columns
    assert results.empty
    assert "future_return_5d" in results.columns
    assert "score_momentum" in results.columns
    assert "net_return_5d" in results.columns
    assert "estimated_capacity" in results.columns
    assert "event_context_type" in results.columns
    assert calibration.empty
    assert "mean_score_final" in calibration.columns
    assert load_source_sla_snapshots_for_dashboard(db_path).empty
    assert "availability_pct" in load_source_sla_snapshots_for_dashboard(db_path).columns
    assert load_observability_snapshots_for_dashboard(db_path).empty
    assert "overall_status" in load_observability_snapshots_for_dashboard(db_path).columns
    assert load_retention_cleanup_runs_for_dashboard(db_path).empty
    assert "rows_candidates" in load_retention_cleanup_runs_for_dashboard(db_path).columns


def test_dashboard_loaders_read_backtest_and_summarize(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO historical_backtest_runs (
                created_at, start_date, end_date, tickers_count, signals_count,
                horizons, mean_return_5d, hit_rate_5d
            ) VALUES ('2026-01-10T10:00:00', '2026-01-01', '2026-01-10', 2, 3, '1,3,5', 1.5, 0.66)
            """
        )
        con.executemany(
            """
            INSERT INTO historical_backtest_results (
                run_id, trade_date, ticker, score_final, signal_type, signal_confidence,
                score_momentum, score_tendencia, score_liquidez, score_volatilidade, score_risco,
                future_return_1d, future_return_3d, future_return_5d, future_return_10d,
                net_return_1d, net_return_3d, net_return_5d, net_return_10d,
                mfe_5d, mae_5d, score_bucket, execution_quality, liquidity_penalty, total_cost_pct,
                total_slippage_pct, is_tradeable
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("2026-01-02", "PETR4", 85, "FORÇA COM LIQUIDEZ", "ALTA", 90, 80, 70, 60, 75, 1, 2, 3, 4, 0.7, 1.7, 2.7, 3.7, 5, -1, "80_100", "EXCELENTE", 0, 0.2, 0.1, 1),
                ("2026-01-03", "PETR4", 65, "OBSERVAR", "MEDIA", 60, 55, 65, 50, 80, -1, 0, 1, 2, -1.3, -0.3, 0.7, 1.7, 3, -2, "60_80", "BOA", 0, 0.2, 0.1, 1),
                ("2026-01-02", "VALE3", 88, "FORÇA COM LIQUIDEZ", "ALTA", 92, 82, 72, 62, 77, 0, 1, 2, 3, -0.3, 0.7, 1.7, 2.7, 4, -1, "80_100", "RUIM", 1, 0.2, 0.1, 0),
            ],
        )
        con.commit()

    latest = load_latest_backtest_run(db_path)
    results = load_backtest_results(db_path, run_id=1)
    signal_summary = load_signal_summary_for_dashboard(db_path)
    bucket_summary = load_score_bucket_summary_for_dashboard(db_path)

    assert latest.loc[0, "id"] == 1
    assert len(results) == 3
    assert "score_liquidez" in results.columns
    net_summary = load_net_summary_for_dashboard(db_path)
    quality = load_execution_quality_summary_for_dashboard(db_path)
    capacity = load_capacity_summary_for_dashboard(db_path)
    assert signal_summary.loc[signal_summary["signal_type"] == "FORÇA COM LIQUIDEZ", "signals"].iloc[0] == 2
    assert bucket_summary.loc[bucket_summary["score_bucket"] == "80_100", "mean_return_5d"].iloc[0] == 2.5
    assert net_summary.loc[0, "tradeable_signals"] == 2
    assert "EXCELENTE" in quality["execution_quality"].tolist()
    assert capacity.empty or "mean_capacity" in capacity.columns


def test_dashboard_loaders_read_calibration_and_component_summary(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO score_calibration_runs (
                created_at, source, total_assets, mean_score_final, p90_score_final,
                count_80_100, inflation_alert, inflation_message
            ) VALUES ('2026-01-10T10:00:00', 'pytest', 2, 70, 90, 1, 0, 'ok')
            """
        )
        con.executemany(
            """
            INSERT INTO score_calibration_assets (
                run_id, captured_at, asset, legacy_score, score_final,
                score_momentum, score_tendencia, score_liquidez, score_volatilidade, score_risco,
                legacy_signal, signal_type, signal_confidence, divergence_type
            ) VALUES (1, '2026-01-10T10:00:00', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("PETR4", 90, 85, 88, 80, 90, 70, 75, "COMPRA/FORÇA", "FORÇA COM LIQUIDEZ", "ALTA", "CONVERGENTE_FORTE"),
                ("ITUB4", 30, 35, 20, 40, 70, 50, 65, "NEUTRO", "SEM ASSIMETRIA", "BAIXA", "CONVERGENTE_FRACO"),
            ],
        )
        con.commit()

    runs = load_calibration_runs_for_dashboard(db_path)
    assets = load_calibration_assets_for_dashboard(db_path, run_id=1)
    history = load_score_distribution_history_for_dashboard(db_path)
    components = load_component_summary_for_dashboard(db_path)

    assert runs.loc[0, "total_assets"] == 2
    assert set(assets["asset"]) == {"PETR4", "ITUB4"}
    assert history.loc[0, "p90_score_final"] == 90
    assert "score_momentum" in components["component"].tolist()
    assert components.loc[components["component"] == "score_liquidez", "mean"].iloc[0] == 80


def test_dashboard_loaders_read_walk_forward_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO walk_forward_runs (
                created_at, start_date, end_date, train_months, test_months, horizon,
                windows_count, positive_windows_pct, mean_test_return,
                mean_test_hit_rate, overfitting_alert
            ) VALUES ('2026-01-10T10:00:00', '2024-01-01', '2026-12-31', 12, 3, 5, 2, 50, 0.5, 0.6, 1)
            """
        )
        con.execute(
            """
            INSERT INTO walk_forward_results (
                run_id, window_id, train_start, train_end, test_start, test_end,
                best_train_signal_type, test_return_best_signal, test_hit_rate_best_signal,
                best_train_score_bucket, test_return_best_bucket, test_hit_rate_best_bucket,
                degradation_score, overfitting_flag
            ) VALUES (1, 1, '2024-01-01', '2024-12-31', '2025-01-01', '2025-03-31',
                      'FORÇA COM LIQUIDEZ', 1.2, 0.6, '80_100', 1.1, 0.55, 0.3, 0)
            """
        )
        con.commit()

    runs = load_walk_forward_runs_for_dashboard(db_path)
    results = load_walk_forward_results_for_dashboard(db_path, run_id=1)

    assert runs.loc[0, "windows_count"] == 2
    assert results.loc[0, "best_train_score_bucket"] == "80_100"


def test_dashboard_loaders_read_filter_and_threshold_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO quality_filter_runs (
                created_at, signals_before, signals_after, removed_pct,
                mean_net_return_before, mean_net_return_after, hit_rate_before, hit_rate_after,
                best_signal_type
            ) VALUES ('2026-01-10T10:00:00', 100, 20, 80, -0.2, 0.1, 0.45, 0.55, 'FORÇA COM LIQUIDEZ')
            """
        )
        con.execute(
            """
            INSERT INTO threshold_optimization_runs (
                created_at, best_params_json, best_mean_net_return, best_hit_rate, best_samples,
                overfitting_warning
            ) VALUES ('2026-01-10T10:00:00', '{}', 0.1, 0.55, 20, 'amostra_insuficiente')
            """
        )
        con.commit()

    filter_runs = load_quality_filter_runs_for_dashboard(db_path)
    threshold_runs = load_threshold_optimization_runs_for_dashboard(db_path)

    assert filter_runs.loc[0, "signals_after"] == 20
    assert threshold_runs.loc[0, "best_samples"] == 20


def test_dashboard_loaders_read_filter_walk_forward_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO filter_walk_forward_runs (
                created_at, start_date, end_date, train_months, test_months, objective,
                windows_count, positive_windows_pct, mean_test_net_return, mean_test_hit_rate,
                avg_test_signals, avg_top_3_concentration_pct, robustness_class, overfitting_alert
            ) VALUES ('2026-01-10T10:00:00', '2026-01-01', '2026-04-30', 1, 1,
                      'mean_net_return_5d', 3, 66.6, 0.1, 0.55, 40, 35, 'PROMISSOR', 0)
            """
        )
        con.execute(
            """
            INSERT INTO filter_walk_forward_results (
                run_id, window_id, train_start, train_end, test_start, test_end,
                best_params_json, train_signals, test_signals,
                train_mean_net_return, test_mean_net_return, train_hit_rate, test_hit_rate,
                top_asset_concentration_pct, top_3_assets_concentration_pct,
                positive_test_window, overfitting_flag, sample_warning, concentration_warning
            ) VALUES (1, 1, '2026-01-01', '2026-01-31', '2026-02-01', '2026-02-28',
                      '{}', 100, 40, 0.2, 0.1, 0.6, 0.55, 20, 45, 1, 0, 0, 0)
            """
        )
        con.commit()

    runs = load_filter_walk_forward_runs_for_dashboard(db_path)
    results = load_filter_walk_forward_results_for_dashboard(db_path, run_id=1)

    assert runs.loc[0, "robustness_class"] == "PROMISSOR"
    assert results.loc[0, "test_signals"] == 40


def test_dashboard_loaders_read_governance_reviews(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO governance_reviews (
                created_at, source_type, source_run_id, candidate_name, governance_status,
                approved, risk_level, confidence_level, total_signals, windows_count,
                positive_windows_pct, mean_net_return, mean_hit_rate,
                avg_top_3_concentration_pct, overfitting_alert, summary_text
            ) VALUES ('2026-01-10T10:00:00', 'filter_walk_forward', 2, 'filtros_v1',
                      'BLOQUEADO_OVERFITTING', 0, 'ALTO', 'BAIXA', 300, 3,
                      33.3, -0.3, 0.46, 36.7, 1, 'bloqueado')
            """
        )
        con.commit()

    reviews = load_governance_reviews_for_dashboard(db_path)
    summary = load_governance_summary_for_dashboard(db_path)

    assert reviews.loc[0, "governance_status"] == "BLOQUEADO_OVERFITTING"
    assert summary.loc[0, "reviews"] == 1


def test_dashboard_loaders_read_market_regime_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO market_regime_daily (
                trade_date, primary_regime, trend_regime, volatility_regime,
                liquidity_regime, risk_regime, regime_confidence, market_return_mean
            ) VALUES ('2026-01-02', 'ALTA_TENDENCIAL', 'ALTA_TENDENCIAL',
                      'BAIXA_VOLATILIDADE', 'LIQUIDEZ_FORTE', 'RISCO_CONTROLADO', 0.75, 1.2)
            """
        )
        con.execute(
            """
            INSERT INTO regime_backtest_summary (
                run_id, regime_type, regime_value, signals_count, mean_net_return_5d,
                hit_rate_5d, tradeable_pct, top_asset_concentration_pct,
                best_signal_type, best_score_bucket, robustness_class
            ) VALUES (1, 'primary_regime', 'ALTA_TENDENCIAL', 100, 0.2, 55, 90, 20,
                      'FORÇA COM LIQUIDEZ', '80_100', 'PROMISSOR')
            """
        )
        con.commit()

    regimes = load_market_regimes_for_dashboard(db_path)
    summary = load_regime_backtest_summary_for_dashboard(db_path, run_id=1)

    assert regimes.loc[0, "primary_regime"] == "ALTA_TENDENCIAL"
    assert summary.loc[0, "robustness_class"] == "PROMISSOR"


def test_dashboard_loaders_read_event_tables_and_summary(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO market_events (
                event_date, ticker, event_type, event_source, event_title,
                impact_direction, impact_score, confidence, created_at
            ) VALUES ('2026-01-05', 'PETR4', 'RESULTADO', 'manual', 'Resultado',
                      'POSITIVO', 0.8, 0.9, '2026-01-05T10:00:00')
            """
        )
        con.execute(
            """
            INSERT INTO historical_backtest_results (
                run_id, trade_date, ticker, score_final, signal_type,
                future_return_5d, net_return_5d, has_event, event_type,
                event_context_type, impact_direction, primary_regime
            ) VALUES (1, '2026-01-05', 'PETR4', 85, 'FORÇA COM LIQUIDEZ',
                      1.0, 0.6, 1, 'RESULTADO', 'MOVIMENTO_EVENT_DRIVEN',
                      'POSITIVO', 'ALTA_TENDENCIAL')
            """
        )
        con.execute(
            """
            INSERT INTO signal_event_links (
                backtest_result_id, ticker, signal_date, event_id, event_date,
                event_type, event_impact_score, days_from_event, link_type, confidence
            ) VALUES (1, 'PETR4', '2026-01-05', 1, '2026-01-05',
                      'RESULTADO', 0.8, 0, 'SAME_DAY', 0.9)
            """
        )
        con.execute(
            """
            INSERT INTO event_context_runs (
                created_at, start_date, end_date, events_count, signals_linked,
                tickers_count, source
            ) VALUES ('2026-01-05T10:00:00', '2026-01-01', '2026-01-31',
                      1, 1, 1, 'pytest')
            """
        )
        con.execute(
            """
            INSERT INTO event_coverage_runs (
                created_at, start_date, end_date, sources, events_loaded, events_after_dedup,
                tickers_count, signals_count, signals_with_event_pct,
                tickers_with_event_pct, coverage_quality
            ) VALUES ('2026-01-05T10:00:00', '2026-01-01', '2026-01-31',
                      'csv,cvm', 3, 2, 1, 1, 1.0, 1.0, 'COBERTURA_BOA')
            """
        )
        con.execute(
            """
            INSERT INTO event_coverage_by_regime (
                coverage_run_id, regime_type, regime_value, signals_count,
                signals_with_event, signals_without_event, signals_with_event_pct,
                dominant_event_type, dominant_event_source, coverage_quality
            ) VALUES (1, 'primary_regime', 'ALTA_TENDENCIAL', 1, 1, 0, 1.0,
                      'RESULTADO', 'manual', 'COBERTURA_BOA')
            """
        )
        con.commit()

    events = load_market_events_for_dashboard(db_path)
    links = load_signal_event_links_for_dashboard(db_path)
    runs = load_event_context_runs_for_dashboard(db_path)
    coverage_runs = load_event_coverage_runs_for_dashboard(db_path)
    coverage_by_regime = load_event_coverage_by_regime_for_dashboard(db_path, coverage_run_id=1)
    summary = load_event_context_summary_for_dashboard(db_path)

    assert events.loc[0, "event_type"] == "RESULTADO"
    assert links.loc[0, "link_type"] == "SAME_DAY"
    assert runs.loc[0, "signals_linked"] == 1
    assert coverage_runs.loc[0, "coverage_quality"] == "COBERTURA_BOA"
    assert coverage_by_regime.loc[0, "regime_value"] == "ALTA_TENDENCIAL"
    assert "event_context_type" in summary["group"].tolist()


def test_dashboard_loaders_read_operation_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO source_health_checks (
                checked_at, source_name, status, available, records_count,
                latest_date, age_days, coverage_hint, path, message, metadata_json
            ) VALUES ('2026-01-05T10:00:00', 'csv', 'OK', 1, 3,
                      '2026-01-05', 0, 'usable', 'events.csv', 'ok', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO daily_routine_runs (
                started_at, finished_at, status, start_date, end_date, sources,
                health_overall_status, event_coverage_quality, events_loaded,
                events_after_dedup, signals_covered_pct, alerts_count
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS_WITH_WARNINGS', '2026-01-01', '2026-01-31',
                      'csv', 'WARNING', 'COBERTURA_FRACA', 3, 3, 0.2, 1)
            """
        )
        con.execute(
            """
            INSERT INTO operational_alerts (
                created_at, alert_type, severity, title, message, source, resolved
            ) VALUES ('2026-01-05T10:00:00', 'SOURCE_STALE', 'WARNING',
                      'Fonte stale', 'stale', 'csv', 0)
            """
        )
        con.execute(
            """
            INSERT INTO source_sla_snapshots (
                created_at, window_days, source_name, total_checks,
                availability_pct, ok_pct, warning_pct, error_pct,
                missing_pct, stale_pct, avg_age_days, max_age_days,
                latest_status, last_ok_at, days_since_last_ok,
                reliability_class, metadata_json
            ) VALUES ('2026-01-05T10:00:00', 30, 'csv', 1,
                      100, 100, 0, 0, 0, 0, 0, 0,
                      'OK', '2026-01-05T10:00:00', 0,
                      'EXCELENTE', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO operational_observability_snapshots (
                created_at, window_days, overall_status, overall_availability_pct,
                total_sources, critical_sources, total_alerts, critical_alerts,
                open_alerts, routine_success_rate_pct, routine_failure_rate_pct,
                avg_signals_covered_pct, coverage_trend_direction,
                summary_text, metadata_json
            ) VALUES ('2026-01-05T10:00:00', 30, 'WARNING', 100,
                      1, 0, 1, 0, 1, 100, 0, 0.2,
                      'INSUFICIENTE', 'summary', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO retention_cleanup_runs (
                started_at, finished_at, dry_run, status, tables_evaluated,
                rows_candidates, rows_archived, rows_deleted, archive_dir,
                warnings_count, errors_count
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      1, 'DRY_RUN', 2, 10, 0, 0, 'data/archive', 0, 0)
            """
        )
        con.execute(
            """
            INSERT INTO retention_cleanup_details (
                run_id, table_name, cutoff_date, rows_total, rows_to_delete,
                rows_archived, rows_deleted, protected, status, archive_path, message
            ) VALUES (1, 'source_health_checks', '2025-01-01', 20, 10,
                      0, 0, 0, 'DRY_RUN', '', 'dry')
            """
        )
        con.commit()

    health = load_source_health_checks_for_dashboard(db_path)
    runs = load_daily_routine_runs_for_dashboard(db_path)
    alerts = load_operational_alerts_for_dashboard(db_path)
    sla = load_source_sla_snapshots_for_dashboard(db_path)
    observability = load_observability_snapshots_for_dashboard(db_path)
    retention_runs = load_retention_cleanup_runs_for_dashboard(db_path)
    retention_details = load_retention_cleanup_details_for_dashboard(db_path, run_id=1)

    assert health.loc[0, "source_name"] == "csv"
    assert runs.loc[0, "status"] == "SUCCESS_WITH_WARNINGS"
    assert alerts.loc[0, "alert_type"] == "SOURCE_STALE"
    assert sla.loc[0, "reliability_class"] == "EXCELENTE"
    assert observability.loc[0, "overall_status"] == "WARNING"
    assert retention_runs.loc[0, "rows_candidates"] == 10
    assert retention_details.loc[0, "table_name"] == "source_health_checks"
