import sqlite3

import pandas as pd

from src.db.init_db import init_database
from src.reports.quant_dashboard_data import (
    load_asset_intelligence_diffs_for_dashboard,
    load_asset_intelligence_snapshots_for_dashboard,
    load_backtest_results,
    load_backtest_runs,
    load_calibration_assets_for_dashboard,
    load_calibration_runs_for_dashboard,
    load_component_summary_for_dashboard,
    load_capacity_summary_for_dashboard,
    load_daily_routine_runs_for_dashboard,
    load_data_source_audit_results_for_dashboard,
    load_data_source_audit_runs_for_dashboard,
    load_data_source_traceability_for_dashboard,
    load_data_reconciliation_results_for_dashboard,
    load_data_reconciliation_runs_for_dashboard,
    load_ingestion_assistant_runs_for_dashboard,
    load_ingestion_assistant_steps_for_dashboard,
    load_ingestion_comparison_for_dashboard,
    load_post_ingestion_validation_for_dashboard,
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
    load_option_scanner_runs_for_dashboard,
    load_option_context_summary_for_dashboard,
    load_option_structure_backtest_results_for_dashboard,
    load_option_structure_backtest_runs_for_dashboard,
    load_option_structure_candidates_for_dashboard,
    load_option_walk_forward_results_for_dashboard,
    load_option_walk_forward_runs_for_dashboard,
    load_options_chain_snapshots_for_dashboard,
    load_regime_backtest_summary_for_dashboard,
    load_retention_cleanup_details_for_dashboard,
    load_retention_cleanup_runs_for_dashboard,
    load_risk_snapshots_for_dashboard,
    load_signal_event_links_for_dashboard,
    load_signal_coverage_by_source_for_dashboard,
    load_signal_coverage_runs_for_dashboard,
    load_latest_backtest_run,
    load_score_bucket_summary_for_dashboard,
    load_score_distribution_history_for_dashboard,
    load_signal_summary_for_dashboard,
    load_source_health_checks_for_dashboard,
    load_source_sla_snapshots_for_dashboard,
    load_technical_backtest_results_for_dashboard,
    load_technical_backtest_runs_for_dashboard,
    load_technical_dedup_runs_for_dashboard,
    load_technical_features_for_dashboard,
    load_technical_setups_for_dashboard,
    load_technical_threshold_runs_for_dashboard,
    load_technical_walk_forward_results_for_dashboard,
    load_technical_walk_forward_runs_for_dashboard,
    load_volatility_estimates_for_dashboard,
    load_position_sizing_for_dashboard,
    load_stress_tests_for_dashboard,
    load_paper_equity_curve_for_dashboard,
    load_paper_cost_sensitivity_for_dashboard,
    load_paper_exit_optimization_results_for_dashboard,
    load_paper_exit_optimization_runs_for_dashboard,
    load_paper_exit_events_for_dashboard,
    load_paper_drawdown_periods_for_dashboard,
    load_paper_fragility_by_asset_for_dashboard,
    load_paper_fragility_by_signal_source_for_dashboard,
    load_paper_fragility_runs_for_dashboard,
    load_paper_hypothesis_block_reasons_for_dashboard,
    load_paper_hypothesis_deep_oos_results_for_dashboard,
    load_paper_hypothesis_deep_oos_runs_for_dashboard,
    load_paper_hypothesis_oos_coverage_for_dashboard,
    load_paper_hypothesis_ranking_results_for_dashboard,
    load_paper_hypothesis_ranking_runs_for_dashboard,
    load_paper_hypothesis_oos_results_for_dashboard,
    load_paper_hypothesis_oos_runs_for_dashboard,
    load_paper_investigation_results_for_dashboard,
    load_paper_investigation_runs_for_dashboard,
    load_paper_orders_for_dashboard,
    load_paper_pnl_attribution_for_dashboard,
    load_paper_positions_for_dashboard,
    load_paper_rebalance_events_for_dashboard,
    load_paper_scenario_validation_results_for_dashboard,
    load_paper_scenario_validation_runs_for_dashboard,
    load_paper_signal_source_comparison_for_dashboard,
    load_paper_simulation_comparisons_for_dashboard,
    load_paper_simulation_runs_for_dashboard,
    load_paper_walk_forward_results_for_dashboard,
    load_paper_walk_forward_runs_for_dashboard,
    load_execution_quality_summary_for_dashboard,
    load_net_summary_for_dashboard,
    load_quality_filter_runs_for_dashboard,
    load_walk_forward_results_for_dashboard,
    load_walk_forward_runs_for_dashboard,
    load_threshold_optimization_runs_for_dashboard,
)


def test_quant_mesa_dashboard_imports_after_integrated_tab():
    import src.reports.quant_mesa_dashboard as dashboard

    assert hasattr(dashboard, "_tab_asset_intelligence")
    assert hasattr(dashboard, "_tab_data_audit")


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
    assert load_data_source_audit_runs_for_dashboard(db_path).empty
    assert load_data_source_audit_results_for_dashboard(db_path).empty
    assert load_data_source_traceability_for_dashboard(db_path).empty
    assert load_data_reconciliation_runs_for_dashboard(db_path).empty
    assert load_data_reconciliation_results_for_dashboard(db_path).empty
    assert load_ingestion_assistant_runs_for_dashboard(db_path).empty
    assert load_ingestion_assistant_steps_for_dashboard(db_path).empty
    assert load_post_ingestion_validation_for_dashboard(db_path).empty
    assert load_ingestion_comparison_for_dashboard(db_path).empty
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
    assert load_option_scanner_runs_for_dashboard(db_path).empty
    assert load_options_chain_snapshots_for_dashboard(db_path).empty
    assert load_option_structure_candidates_for_dashboard(db_path).empty
    assert load_option_structure_backtest_runs_for_dashboard(db_path).empty
    assert load_option_structure_backtest_results_for_dashboard(db_path).empty
    assert load_option_walk_forward_runs_for_dashboard(db_path).empty
    assert load_option_walk_forward_results_for_dashboard(db_path).empty
    assert load_option_context_summary_for_dashboard(db_path).empty
    assert load_technical_features_for_dashboard(db_path).empty
    assert load_technical_setups_for_dashboard(db_path).empty
    assert load_technical_backtest_runs_for_dashboard(db_path).empty
    assert load_technical_backtest_results_for_dashboard(db_path).empty
    assert load_technical_walk_forward_runs_for_dashboard(db_path).empty
    assert load_technical_walk_forward_results_for_dashboard(db_path).empty
    assert load_technical_threshold_runs_for_dashboard(db_path).empty
    assert load_technical_dedup_runs_for_dashboard(db_path).empty
    assert load_asset_intelligence_snapshots_for_dashboard(db_path).empty
    assert load_asset_intelligence_diffs_for_dashboard(db_path).empty
    assert load_risk_snapshots_for_dashboard(db_path).empty
    assert load_volatility_estimates_for_dashboard(db_path).empty
    assert load_position_sizing_for_dashboard(db_path).empty
    assert load_stress_tests_for_dashboard(db_path).empty
    assert load_paper_simulation_runs_for_dashboard(db_path).empty
    assert load_paper_orders_for_dashboard(db_path).empty
    assert load_paper_positions_for_dashboard(db_path).empty
    assert load_paper_equity_curve_for_dashboard(db_path).empty
    assert load_paper_exit_events_for_dashboard(db_path).empty
    assert load_paper_rebalance_events_for_dashboard(db_path).empty
    assert load_paper_pnl_attribution_for_dashboard(db_path).empty
    assert load_paper_simulation_comparisons_for_dashboard(db_path).empty
    assert load_paper_exit_optimization_runs_for_dashboard(db_path).empty
    assert load_paper_exit_optimization_results_for_dashboard(db_path).empty
    assert load_paper_walk_forward_runs_for_dashboard(db_path).empty
    assert load_paper_walk_forward_results_for_dashboard(db_path).empty
    assert load_paper_scenario_validation_runs_for_dashboard(db_path).empty
    assert load_paper_scenario_validation_results_for_dashboard(db_path).empty
    assert load_paper_cost_sensitivity_for_dashboard(db_path).empty
    assert load_paper_signal_source_comparison_for_dashboard(db_path).empty
    assert load_paper_fragility_runs_for_dashboard(db_path).empty
    assert load_paper_fragility_by_asset_for_dashboard(db_path).empty
    assert load_paper_fragility_by_signal_source_for_dashboard(db_path).empty
    assert load_paper_drawdown_periods_for_dashboard(db_path).empty
    assert load_paper_investigation_runs_for_dashboard(db_path).empty
    assert load_paper_investigation_results_for_dashboard(db_path).empty
    assert load_paper_hypothesis_oos_runs_for_dashboard(db_path).empty
    assert load_paper_hypothesis_oos_results_for_dashboard(db_path).empty
    assert load_paper_hypothesis_oos_coverage_for_dashboard(db_path).empty
    assert load_paper_hypothesis_ranking_runs_for_dashboard(db_path).empty
    assert load_paper_hypothesis_ranking_results_for_dashboard(db_path).empty
    assert load_paper_hypothesis_deep_oos_runs_for_dashboard(db_path).empty
    assert load_paper_hypothesis_deep_oos_results_for_dashboard(db_path).empty
    assert load_paper_hypothesis_block_reasons_for_dashboard(db_path).empty
    assert load_signal_coverage_runs_for_dashboard(db_path).empty
    assert load_signal_coverage_by_source_for_dashboard(db_path).empty


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
    assert load_option_scanner_runs_for_dashboard(db_path).empty
    assert "options_count" in load_option_scanner_runs_for_dashboard(db_path).columns
    assert load_options_chain_snapshots_for_dashboard(db_path).empty
    assert "option_ticker" in load_options_chain_snapshots_for_dashboard(db_path).columns
    assert load_option_structure_candidates_for_dashboard(db_path).empty
    assert "structure_score" in load_option_structure_candidates_for_dashboard(db_path).columns
    assert load_option_structure_backtest_runs_for_dashboard(db_path).empty
    assert "mean_net_return" in load_option_structure_backtest_runs_for_dashboard(db_path).columns
    assert load_option_structure_backtest_results_for_dashboard(db_path).empty
    assert "net_return" in load_option_structure_backtest_results_for_dashboard(db_path).columns
    assert load_option_walk_forward_runs_for_dashboard(db_path).empty
    assert "robustness_class" in load_option_walk_forward_runs_for_dashboard(db_path).columns
    assert load_option_walk_forward_results_for_dashboard(db_path).empty
    assert "test_mean_net_return" in load_option_walk_forward_results_for_dashboard(db_path).columns
    assert load_option_context_summary_for_dashboard(db_path).empty
    assert "context_type" in load_option_context_summary_for_dashboard(db_path).columns
    assert load_technical_features_for_dashboard(db_path).empty
    assert "technical_score_final" in load_technical_features_for_dashboard(db_path).columns
    assert load_technical_setups_for_dashboard(db_path).empty
    assert "setup_type" in load_technical_setups_for_dashboard(db_path).columns
    assert load_technical_backtest_runs_for_dashboard(db_path).empty
    assert "mean_return_5d" in load_technical_backtest_runs_for_dashboard(db_path).columns
    assert load_technical_backtest_results_for_dashboard(db_path).empty
    assert "future_return_5d" in load_technical_backtest_results_for_dashboard(db_path).columns
    assert load_technical_walk_forward_runs_for_dashboard(db_path).empty
    assert "robustness_class" in load_technical_walk_forward_runs_for_dashboard(db_path).columns
    assert load_technical_walk_forward_results_for_dashboard(db_path).empty
    assert "test_mean_return" in load_technical_walk_forward_results_for_dashboard(db_path).columns
    assert load_technical_threshold_runs_for_dashboard(db_path).empty
    assert "best_params_json" in load_technical_threshold_runs_for_dashboard(db_path).columns
    assert load_technical_dedup_runs_for_dashboard(db_path).empty
    assert "removed_pct" in load_technical_dedup_runs_for_dashboard(db_path).columns
    assert load_asset_intelligence_snapshots_for_dashboard(db_path).empty
    assert "integrated_status" in load_asset_intelligence_snapshots_for_dashboard(db_path).columns
    assert load_asset_intelligence_diffs_for_dashboard(db_path).empty
    assert "material_change_type" in load_asset_intelligence_diffs_for_dashboard(db_path).columns
    assert load_risk_snapshots_for_dashboard(db_path).empty
    assert "risk_status" in load_risk_snapshots_for_dashboard(db_path).columns
    assert load_volatility_estimates_for_dashboard(db_path).empty
    assert "ensemble_vol" in load_volatility_estimates_for_dashboard(db_path).columns
    assert load_position_sizing_for_dashboard(db_path).empty
    assert "limiting_factor" in load_position_sizing_for_dashboard(db_path).columns
    assert load_stress_tests_for_dashboard(db_path).empty
    assert "scenario" in load_stress_tests_for_dashboard(db_path).columns
    assert load_paper_simulation_runs_for_dashboard(db_path).empty
    assert "governance_status" in load_paper_simulation_runs_for_dashboard(db_path).columns
    assert load_paper_orders_for_dashboard(db_path).empty
    assert "order_status" in load_paper_orders_for_dashboard(db_path).columns
    assert load_paper_positions_for_dashboard(db_path).empty
    assert "market_value" in load_paper_positions_for_dashboard(db_path).columns
    assert load_paper_equity_curve_for_dashboard(db_path).empty
    assert "equity" in load_paper_equity_curve_for_dashboard(db_path).columns
    assert load_paper_exit_events_for_dashboard(db_path).empty
    assert "exit_rule_triggered" in load_paper_exit_events_for_dashboard(db_path).columns
    assert load_paper_rebalance_events_for_dashboard(db_path).empty
    assert "target_weight" in load_paper_rebalance_events_for_dashboard(db_path).columns
    assert load_paper_pnl_attribution_for_dashboard(db_path).empty
    assert "contribution_pct" in load_paper_pnl_attribution_for_dashboard(db_path).columns
    assert load_paper_simulation_comparisons_for_dashboard(db_path).empty
    assert "material_change" in load_paper_simulation_comparisons_for_dashboard(db_path).columns
    assert load_paper_exit_optimization_runs_for_dashboard(db_path).empty
    assert "best_params_json" in load_paper_exit_optimization_runs_for_dashboard(db_path).columns
    assert load_paper_exit_optimization_results_for_dashboard(db_path).empty
    assert "score_objective" in load_paper_exit_optimization_results_for_dashboard(db_path).columns
    assert load_paper_walk_forward_runs_for_dashboard(db_path).empty
    assert "robustness_class" in load_paper_walk_forward_runs_for_dashboard(db_path).columns
    assert load_paper_walk_forward_results_for_dashboard(db_path).empty
    assert "overfitting_flag" in load_paper_walk_forward_results_for_dashboard(db_path).columns
    assert load_paper_scenario_validation_runs_for_dashboard(db_path).empty
    assert "positive_periods_pct" in load_paper_scenario_validation_runs_for_dashboard(db_path).columns
    assert load_paper_scenario_validation_results_for_dashboard(db_path).empty
    assert "scenario_name" in load_paper_scenario_validation_results_for_dashboard(db_path).columns
    assert load_paper_cost_sensitivity_for_dashboard(db_path).empty
    assert "cost_robustness_class" in load_paper_cost_sensitivity_for_dashboard(db_path).columns
    assert load_paper_signal_source_comparison_for_dashboard(db_path).empty
    assert "robustness_class" in load_paper_signal_source_comparison_for_dashboard(db_path).columns
    assert load_paper_fragility_runs_for_dashboard(db_path).empty
    assert "fragility_score" in load_paper_fragility_runs_for_dashboard(db_path).columns
    assert load_paper_fragility_by_asset_for_dashboard(db_path).empty
    assert "ticker" in load_paper_fragility_by_asset_for_dashboard(db_path).columns
    assert load_paper_fragility_by_signal_source_for_dashboard(db_path).empty
    assert "signal_source" in load_paper_fragility_by_signal_source_for_dashboard(db_path).columns
    assert load_paper_drawdown_periods_for_dashboard(db_path).empty
    assert "drawdown_trough" in load_paper_drawdown_periods_for_dashboard(db_path).columns
    assert load_signal_coverage_runs_for_dashboard(db_path).empty
    assert "coverage_status" in load_signal_coverage_runs_for_dashboard(db_path).columns
    assert load_signal_coverage_by_source_for_dashboard(db_path).empty
    assert "requirements_status" in load_signal_coverage_by_source_for_dashboard(db_path).columns
    assert load_paper_hypothesis_ranking_runs_for_dashboard(db_path).empty
    assert "best_hypothesis_id" in load_paper_hypothesis_ranking_runs_for_dashboard(db_path).columns
    assert load_paper_hypothesis_ranking_results_for_dashboard(db_path).empty
    assert "hypothesis_robustness_score" in load_paper_hypothesis_ranking_results_for_dashboard(db_path).columns
    assert load_paper_hypothesis_deep_oos_runs_for_dashboard(db_path).empty
    assert "best_hypothesis_id" in load_paper_hypothesis_deep_oos_runs_for_dashboard(db_path).columns
    assert load_paper_hypothesis_deep_oos_results_for_dashboard(db_path).empty
    assert "block_reason" in load_paper_hypothesis_deep_oos_results_for_dashboard(db_path).columns
    assert load_paper_hypothesis_block_reasons_for_dashboard(db_path).empty
    assert "primary_block_reason" in load_paper_hypothesis_block_reasons_for_dashboard(db_path).columns


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


def test_dashboard_loaders_read_options_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO option_scanner_runs (
                started_at, finished_at, status, options_count, structures_count,
                approved_for_study_count, blocked_count, warning_count, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS', 2, 1, 1, 0, 0, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO options_chain_snapshots (
                captured_at, trade_date, option_ticker, underlying, option_type,
                strike, maturity_date, days_to_maturity, last_price, bid, ask,
                spread_pct, volume, trades, financial_volume, underlying_price,
                moneyness_pct, moneyness_class, intrinsic_value, extrinsic_value,
                breakeven, implied_volatility, historical_volatility, delta,
                gamma, theta, vega, liquidity_score, risk_score, metadata_json
            ) VALUES ('2026-01-05T10:01:00', '2026-01-05', 'PETRA300',
                      'PETR4', 'CALL', 30, '2026-02-20', 46, 1.2, 1.1, 1.3,
                      16.67, 10000, 80, 120000, 31, 3.33, 'ATM', 1, 0.2,
                      31.2, 0.35, 0.30, 0.55, 0.08, -0.01, 0.10, 80, 70, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_structure_candidates (
                created_at, structure_type, underlying, maturity_date, legs_json,
                net_debit, net_credit, max_profit, max_loss, breakeven,
                payoff_ratio, liquidity_score, risk_score, structure_score,
                candidate_status, explanation, governance_status, metadata_json
            ) VALUES ('2026-01-05T10:01:00', 'LONG_CALL', 'PETR4',
                      '2026-02-20', '[]', 120, 0, NULL, 120, 31.2,
                      2.0, 80, 70, 74, 'ASSIMETRIA_A_INVESTIGAR',
                      'Estrutura para estudo, não recomendação.',
                      'STRUCTURE_APPROVED_FOR_STUDY', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_structure_backtest_runs (
                started_at, finished_at, status, start_date, end_date,
                underlyings, structure_type, entries_count, completed_count,
                skipped_count, mean_net_return, win_rate, profit_factor,
                avg_cost_drag, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS', '2026-01-01', '2026-01-31', 'PETR4',
                      'LONG_CALL', 2, 1, 1, 0.5, 50, 1.2, 2.0, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_structure_backtest_results (
                run_id, entry_date, exit_date, underlying, structure_type,
                maturity_date, dte_entry, dte_exit, legs_json, entry_debit,
                entry_credit, exit_value, gross_pnl, net_pnl, gross_return,
                net_return, max_loss, return_on_risk, exit_reason,
                liquidity_score, spread_cost, transaction_cost, slippage_cost,
                execution_quality, status, metadata_json
            ) VALUES (1, '2026-01-02', '2026-01-07', 'PETR4', 'LONG_CALL',
                      '2026-02-20', 40, 35, '[]', 100, 0, 120, 20, 18,
                      20, 18, 100, 18, 'HOLDING_DAYS', 80, 1, 1, 1,
                      'BOA', 'COMPLETED', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_walk_forward_runs (
                started_at, finished_at, status, start_date, end_date,
                structure_type, train_months, test_months, windows_count,
                positive_windows_pct, mean_test_net_return, mean_test_win_rate,
                mean_test_profit_factor, robustness_class, governance_status,
                metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS', '2026-01-01', '2026-04-30', 'LONG_CALL',
                      3, 1, 2, 50, 0.1, 52, 1.1, 'OPTIONS_WF_PROMISSOR',
                      'OPTIONS_OOS_OBSERVATION_ONLY', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_walk_forward_results (
                run_id, window_id, train_start, train_end, test_start, test_end,
                train_trades, test_trades, train_mean_net_return,
                test_mean_net_return, train_win_rate, test_win_rate,
                train_profit_factor, test_profit_factor, avg_cost_drag,
                skipped_pct, positive_test_window, overfitting_flag,
                insufficient_data_flag, metadata_json
            ) VALUES (1, 1, '2026-01-01', '2026-03-31',
                      '2026-04-01', '2026-04-30', 10, 5, 0.2, 0.1,
                      55, 52, 1.2, 1.1, 1, 0, 1, 0, 0, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO option_context_summary (
                run_id, context_type, context_value, trades, mean_net_return,
                win_rate, profit_factor, avg_cost_drag, skipped_pct,
                metadata_json
            ) VALUES (1, 'dte_bucket', '16_30', 5, 0.1, 52, 1.1, 1, 0, '{}')
            """
        )
        con.commit()

    runs = load_option_scanner_runs_for_dashboard(db_path)
    chain = load_options_chain_snapshots_for_dashboard(db_path)
    structures = load_option_structure_candidates_for_dashboard(db_path)
    bt_runs = load_option_structure_backtest_runs_for_dashboard(db_path)
    bt_results = load_option_structure_backtest_results_for_dashboard(db_path, run_id=1)
    wf_runs = load_option_walk_forward_runs_for_dashboard(db_path)
    wf_results = load_option_walk_forward_results_for_dashboard(db_path, run_id=1)
    context = load_option_context_summary_for_dashboard(db_path, run_id=1)

    assert runs.loc[0, "options_count"] == 2
    assert chain.loc[0, "option_ticker"] == "PETRA300"
    assert structures.loc[0, "governance_status"] == "STRUCTURE_APPROVED_FOR_STUDY"
    assert bt_runs.loc[0, "structure_type"] == "LONG_CALL"
    assert bt_results.loc[0, "net_return"] == 18
    assert wf_runs.loc[0, "robustness_class"] == "OPTIONS_WF_PROMISSOR"
    assert wf_results.loc[0, "test_trades"] == 5
    assert context.loc[0, "context_value"] == "16_30"


def test_dashboard_loaders_read_technical_tables(tmp_path):
    db_path = tmp_path / "scanner_quant.db"
    init_database(db_path, verbose=False)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            INSERT INTO technical_feature_snapshots (
                created_at, trade_date, ticker, trend_score, momentum_score,
                volatility_score, volume_score, breakout_score,
                support_resistance_score, pattern_score, risk_score,
                technical_score_final, technical_status, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05', 'PETR4',
                      80, 75, 60, 90, 80, 65, 60, 70, 76,
                      'TECNICO_PROMISSOR', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_setup_signals (
                created_at, trade_date, ticker, setup_type, setup_score,
                setup_confidence, setup_direction, trigger_price,
                invalidation_price, target_hint, risk_hint, technical_status,
                governance_status, explanation, reasons_for_json,
                reasons_against_json, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05', 'PETR4',
                      'BREAKOUT_VOLUME', 80, 0.7, 'BULLISH', 30,
                      28, 34, 2, 'TECNICO_PROMISSOR',
                      'TECH_OBSERVATION_ONLY', 'padrão a investigar',
                      '[]', '[]', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_backtest_runs (
                started_at, finished_at, status, setup_type, start_date,
                end_date, signals_count, mean_return_5d, hit_rate_5d,
                governance_status, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS', 'BREAKOUT_VOLUME', '2026-01-01',
                      '2026-01-31', 1, 1.2, 100,
                      'TECH_BLOCKED_INSUFFICIENT_DATA', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_backtest_results (
                run_id, trade_date, ticker, setup_type, technical_score_final,
                technical_status, future_return_1d, future_return_3d,
                future_return_5d, future_return_10d, hit_1d, hit_3d,
                hit_5d, hit_10d, metadata_json
            ) VALUES (1, '2026-01-05', 'PETR4', 'BREAKOUT_VOLUME',
                      76, 'TECNICO_PROMISSOR', 0.2, 0.5, 1.2, 2.0,
                      1, 1, 1, 1, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_walk_forward_runs (
                started_at, finished_at, status, start_date, end_date,
                train_months, test_months, setup_type, windows_count,
                positive_windows_pct, mean_test_return, mean_test_hit_rate,
                robustness_class, governance_status, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-05T10:01:00',
                      'SUCCESS', '2026-01-01', '2026-04-30', 3, 1,
                      'BREAKOUT_VOLUME', 1, 100, 0.5, 60,
                      'TECH_WF_PROMISSOR', 'TECH_OOS_OBSERVATION_ONLY', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_walk_forward_results (
                run_id, window_id, train_start, train_end, test_start, test_end,
                setup_type, best_params_json, train_signals, test_signals,
                train_mean_return, test_mean_return, train_hit_rate, test_hit_rate,
                test_positive, overfitting_flag, insufficient_data_flag,
                concentration_warning, stability_warning, metadata_json
            ) VALUES (1, 1, '2026-01-01', '2026-03-31',
                      '2026-04-01', '2026-04-30', 'BREAKOUT_VOLUME',
                      '{}', 100, 30, 0.7, 0.5, 60, 58, 1, 0, 0, 0, 0, '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_threshold_optimization_runs (
                created_at, start_date, end_date, objective, best_params_json,
                best_mean_return, best_hit_rate, best_samples,
                overfitting_warning, metadata_json
            ) VALUES ('2026-01-05T10:00:00', '2026-01-01',
                      '2026-04-30', 'mean_return_5d', '{}', 0.5,
                      60, 100, 'OK', '{}')
            """
        )
        con.execute(
            """
            INSERT INTO technical_setup_dedup_runs (
                created_at, signals_before, signals_after, removed_count,
                removed_pct, top_redundant_setups_json, metadata_json
            ) VALUES ('2026-01-05T10:00:00', 10, 6, 4, 40, '{}', '{}')
            """
        )
        con.commit()

    assert load_technical_features_for_dashboard(db_path).loc[0, "technical_status"] == "TECNICO_PROMISSOR"
    assert load_technical_setups_for_dashboard(db_path).loc[0, "setup_type"] == "BREAKOUT_VOLUME"
    assert load_technical_backtest_runs_for_dashboard(db_path).loc[0, "signals_count"] == 1
    assert load_technical_backtest_results_for_dashboard(db_path, run_id=1).loc[0, "future_return_5d"] == 1.2
    assert load_technical_walk_forward_runs_for_dashboard(db_path).loc[0, "robustness_class"] == "TECH_WF_PROMISSOR"
    assert load_technical_walk_forward_results_for_dashboard(db_path, run_id=1).loc[0, "test_signals"] == 30
    assert load_technical_threshold_runs_for_dashboard(db_path).loc[0, "best_samples"] == 100
    assert load_technical_dedup_runs_for_dashboard(db_path).loc[0, "removed_count"] == 4
