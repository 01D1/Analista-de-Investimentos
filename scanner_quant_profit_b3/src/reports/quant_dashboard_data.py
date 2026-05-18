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

DATA_SOURCE_AUDIT_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "sources_checked",
    "ok_count",
    "warning_count",
    "error_count",
    "missing_count",
    "overall_reliability_score",
    "overall_status",
    "metadata_json",
]

DATA_SOURCE_AUDIT_RESULT_COLUMNS = [
    "id",
    "run_id",
    "source_name",
    "source_type",
    "primary_or_secondary",
    "available",
    "records_count",
    "latest_date",
    "tickers_count",
    "coverage_scope",
    "status",
    "reliability_score",
    "reliability_class",
    "message",
    "metadata_json",
]

DATA_SOURCE_TRACEABILITY_COLUMNS = [
    "id",
    "created_at",
    "ticker",
    "data_domain",
    "source_name",
    "source_type",
    "source_url_or_path",
    "source_date",
    "collected_at",
    "record_count",
    "checksum",
    "metadata_json",
]

DATA_FILE_MANIFEST_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "files_count",
    "new_files_count",
    "changed_files_count",
    "removed_files_count",
    "status",
    "metadata_json",
]

DATA_FILE_MANIFEST_COLUMNS = [
    "id",
    "created_at",
    "file_path",
    "file_name",
    "extension",
    "size_bytes",
    "modified_at",
    "checksum",
    "source_domain",
    "active",
    "metadata_json",
]

DATA_RECONCILIATION_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "reconciliation_type",
    "status",
    "issues_count",
    "fixes_suggested_count",
    "fixes_executed_count",
    "metadata_json",
]

DATA_RECONCILIATION_RESULT_COLUMNS = [
    "id",
    "run_id",
    "source_domain",
    "issue_type",
    "severity",
    "status",
    "description",
    "suggested_command",
    "executed",
    "execution_status",
    "metadata_json",
]

INGESTION_ASSISTANT_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "dry_run",
    "executed",
    "status",
    "sources",
    "steps_total",
    "steps_executed",
    "steps_failed",
    "manual_steps",
    "improvements_count",
    "metadata_json",
]

INGESTION_ASSISTANT_STEP_COLUMNS = [
    "id",
    "run_id",
    "step_id",
    "step_order",
    "source_domain",
    "step_type",
    "title",
    "suggested_command",
    "can_execute",
    "requires_confirm",
    "risk_level",
    "status",
    "stdout",
    "stderr",
    "metadata_json",
]

POST_INGESTION_VALIDATION_COLUMNS = [
    "id",
    "run_id",
    "source_domain",
    "validation_status",
    "before_status",
    "after_status",
    "improvement_detected",
    "records_before",
    "records_after",
    "latest_date_before",
    "latest_date_after",
    "message",
    "metadata_json",
]

INGESTION_COMPARISON_COLUMNS = [
    "id",
    "run_id",
    "source_name",
    "before_score",
    "after_score",
    "score_delta",
    "before_status",
    "after_status",
    "status_improved",
    "records_delta",
    "freshness_improved",
    "message",
    "metadata_json",
]

OPTIONS_CHAIN_SNAPSHOT_COLUMNS = [
    "id",
    "captured_at",
    "trade_date",
    "option_ticker",
    "underlying",
    "option_type",
    "strike",
    "maturity_date",
    "days_to_maturity",
    "last_price",
    "bid",
    "ask",
    "spread_pct",
    "volume",
    "trades",
    "financial_volume",
    "open_interest",
    "underlying_price",
    "moneyness_pct",
    "moneyness_class",
    "intrinsic_value",
    "extrinsic_value",
    "breakeven",
    "implied_volatility",
    "historical_volatility",
    "delta",
    "gamma",
    "theta",
    "vega",
    "liquidity_score",
    "risk_score",
    "metadata_json",
]

OPTION_STRUCTURE_CANDIDATE_COLUMNS = [
    "id",
    "created_at",
    "structure_type",
    "underlying",
    "maturity_date",
    "legs_json",
    "net_debit",
    "net_credit",
    "max_profit",
    "max_loss",
    "breakeven",
    "payoff_ratio",
    "liquidity_score",
    "risk_score",
    "structure_score",
    "candidate_status",
    "explanation",
    "governance_status",
    "metadata_json",
]

OPTION_SCANNER_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "options_count",
    "structures_count",
    "approved_for_study_count",
    "blocked_count",
    "warning_count",
    "metadata_json",
]

OPTION_STRUCTURE_BACKTEST_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "underlyings",
    "structure_type",
    "entries_count",
    "completed_count",
    "skipped_count",
    "mean_net_return",
    "win_rate",
    "profit_factor",
    "avg_cost_drag",
    "metadata_json",
]

OPTION_STRUCTURE_BACKTEST_RESULT_COLUMNS = [
    "id",
    "run_id",
    "entry_date",
    "exit_date",
    "underlying",
    "structure_type",
    "maturity_date",
    "dte_entry",
    "dte_exit",
    "legs_json",
    "entry_debit",
    "entry_credit",
    "exit_value",
    "gross_pnl",
    "net_pnl",
    "gross_return",
    "net_return",
    "max_loss",
    "return_on_risk",
    "exit_reason",
    "liquidity_score",
    "spread_cost",
    "transaction_cost",
    "slippage_cost",
    "execution_quality",
    "status",
    "metadata_json",
]

OPTION_WALK_FORWARD_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "structure_type",
    "train_months",
    "test_months",
    "windows_count",
    "positive_windows_pct",
    "mean_test_net_return",
    "mean_test_win_rate",
    "mean_test_profit_factor",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

OPTION_WALK_FORWARD_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "train_trades",
    "test_trades",
    "train_mean_net_return",
    "test_mean_net_return",
    "train_win_rate",
    "test_win_rate",
    "train_profit_factor",
    "test_profit_factor",
    "avg_cost_drag",
    "skipped_pct",
    "positive_test_window",
    "overfitting_flag",
    "insufficient_data_flag",
    "metadata_json",
]

OPTION_CONTEXT_SUMMARY_COLUMNS = [
    "id",
    "run_id",
    "context_type",
    "context_value",
    "trades",
    "mean_net_return",
    "win_rate",
    "profit_factor",
    "avg_cost_drag",
    "skipped_pct",
    "metadata_json",
]

TECHNICAL_FEATURE_COLUMNS = [
    "id",
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

TECHNICAL_SETUP_COLUMNS = [
    "id",
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

TECHNICAL_BACKTEST_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "setup_type",
    "start_date",
    "end_date",
    "signals_count",
    "mean_return_5d",
    "hit_rate_5d",
    "governance_status",
    "metadata_json",
]

TECHNICAL_BACKTEST_RESULT_COLUMNS = [
    "id",
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

TECHNICAL_WALK_FORWARD_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "setup_type",
    "windows_count",
    "positive_windows_pct",
    "mean_test_return",
    "mean_test_hit_rate",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

TECHNICAL_WALK_FORWARD_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "setup_type",
    "best_params_json",
    "train_signals",
    "test_signals",
    "train_mean_return",
    "test_mean_return",
    "train_hit_rate",
    "test_hit_rate",
    "test_positive",
    "overfitting_flag",
    "insufficient_data_flag",
    "concentration_warning",
    "stability_warning",
    "metadata_json",
]

TECHNICAL_THRESHOLD_OPTIMIZATION_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "objective",
    "best_params_json",
    "best_mean_return",
    "best_hit_rate",
    "best_samples",
    "overfitting_warning",
    "metadata_json",
]

TECHNICAL_SETUP_DEDUP_RUN_COLUMNS = [
    "id",
    "created_at",
    "signals_before",
    "signals_after",
    "removed_count",
    "removed_pct",
    "top_redundant_setups_json",
    "metadata_json",
]

ASSET_INTELLIGENCE_COLUMNS = [
    "id",
    "created_at",
    "trade_date",
    "ticker",
    "company_name",
    "sector",
    "subsector",
    "market_price",
    "technical_score_final",
    "technical_status",
    "top_technical_setup",
    "technical_setup_score",
    "technical_setup_confidence",
    "technical_governance_status",
    "technical_oos_status",
    "technical_explanation",
    "quant_score",
    "quant_signal_type",
    "quant_signal_confidence",
    "quant_governance_status",
    "quant_explanation",
    "valuation_available",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "valuation_governance_status",
    "has_recent_event",
    "event_type",
    "event_context_type",
    "event_impact_score",
    "event_coverage_quality",
    "event_governance_status",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
    "regime_governance_status",
    "option_available",
    "best_option_structure_type",
    "option_structure_score",
    "option_oos_governance_status",
    "option_liquidity_score",
    "option_execution_quality",
    "option_explanation",
    "ensemble_vol",
    "var_95",
    "expected_shortfall_95",
    "recommended_size",
    "recommended_position_value",
    "risk_status",
    "risk_limiting_factor",
    "risk_explanation",
    "integrated_score",
    "integrated_status",
    "integrated_confidence",
    "integrated_governance_status",
    "data_quality_score",
    "governance_blocked",
    "explanation",
    "reasons_for_json",
    "reasons_against_json",
    "required_actions_json",
    "metadata_json",
]

VOLATILITY_ESTIMATE_COLUMNS = [
    "id",
    "created_at",
    "trade_date",
    "ticker",
    "vol_5d",
    "vol_10d",
    "vol_20d",
    "vol_60d",
    "vol_252d",
    "vol_ewma",
    "downside_vol",
    "parkinson_vol",
    "garman_klass_vol",
    "atr_vol",
    "ensemble_vol",
    "volatility_regime",
    "metadata_json",
]

RISK_SNAPSHOT_COLUMNS = [
    "id",
    "created_at",
    "trade_date",
    "ticker",
    "price",
    "position_value",
    "ensemble_vol",
    "volatility_regime",
    "parametric_var_95",
    "historical_var_95",
    "expected_shortfall_95",
    "recommended_size",
    "recommended_position_value",
    "limiting_factor",
    "risk_status",
    "explanation",
    "metadata_json",
]

POSITION_SIZING_COLUMNS = [
    "id",
    "created_at",
    "trade_date",
    "ticker",
    "capital",
    "risk_pct",
    "entry_price",
    "stop_price",
    "atr",
    "volatility",
    "avg_financial_volume",
    "size_fixed_risk",
    "size_atr",
    "size_var",
    "size_liquidity",
    "final_size",
    "final_position_value",
    "limiting_factor",
    "estimated_var",
    "metadata_json",
]

STRESS_TEST_RESULT_COLUMNS = [
    "id",
    "created_at",
    "ticker",
    "scenario",
    "position_value",
    "estimated_loss",
    "loss_pct",
    "metadata_json",
]

PAPER_SIMULATION_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "capital_initial",
    "capital_final",
    "total_return",
    "sharpe",
    "sortino",
    "max_drawdown",
    "trades_count",
    "win_rate",
    "profit_factor",
    "governance_status",
    "metadata_json",
]

PAPER_ORDER_COLUMNS = [
    "id",
    "run_id",
    "created_at",
    "trade_date",
    "ticker",
    "side",
    "quantity",
    "theoretical_price",
    "simulated_execution_price",
    "execution_cost",
    "slippage_cost",
    "order_status",
    "signal_source",
    "rejection_reason",
    "metadata_json",
]

PAPER_POSITION_COLUMNS = [
    "id",
    "run_id",
    "trade_date",
    "ticker",
    "quantity",
    "avg_price",
    "market_price",
    "market_value",
    "unrealized_pnl",
    "realized_pnl",
    "var_95",
    "expected_shortfall_95",
    "metadata_json",
]

PAPER_EQUITY_COLUMNS = [
    "id",
    "run_id",
    "trade_date",
    "cash",
    "equity",
    "exposure",
    "daily_return",
    "drawdown",
    "portfolio_var_95",
    "portfolio_es_95",
    "metadata_json",
]

PAPER_EXIT_EVENT_COLUMNS = [
    "id",
    "run_id",
    "trade_date",
    "ticker",
    "position_id",
    "exit_rule_triggered",
    "exit_reason",
    "exit_price",
    "pnl",
    "metadata_json",
]

PAPER_REBALANCE_EVENT_COLUMNS = [
    "id",
    "run_id",
    "trade_date",
    "ticker",
    "action",
    "current_weight",
    "target_weight",
    "order_quantity",
    "reason",
    "metadata_json",
]

PAPER_PNL_ATTRIBUTION_COLUMNS = [
    "id",
    "run_id",
    "attribution_type",
    "bucket",
    "trades",
    "gross_pnl",
    "net_pnl",
    "win_rate",
    "avg_return",
    "contribution_pct",
    "metadata_json",
]

PAPER_SIMULATION_COMPARISON_COLUMNS = [
    "id",
    "created_at",
    "simple_run_id",
    "advanced_run_id",
    "metric",
    "simple_value",
    "advanced_value",
    "delta",
    "improved",
    "material_change",
    "metadata_json",
]

PAPER_EXIT_OPTIMIZATION_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "objective",
    "best_params_json",
    "best_total_return",
    "best_max_drawdown",
    "best_profit_factor",
    "best_trades_count",
    "overfitting_warning",
    "metadata_json",
]

PAPER_EXIT_OPTIMIZATION_RESULT_COLUMNS = [
    "id",
    "run_id",
    "params_json",
    "total_return",
    "max_drawdown",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
    "trades_count",
    "turnover",
    "score_objective",
    "overfit_risk_hint",
    "metadata_json",
]

PAPER_WALK_FORWARD_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "train_months",
    "test_months",
    "windows_count",
    "positive_windows_pct",
    "mean_test_return",
    "mean_test_drawdown",
    "mean_test_profit_factor",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

PAPER_WALK_FORWARD_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "best_params_json",
    "train_return",
    "test_return",
    "train_drawdown",
    "test_drawdown",
    "train_profit_factor",
    "test_profit_factor",
    "train_trades",
    "test_trades",
    "test_positive",
    "overfitting_flag",
    "turnover_warning",
    "drawdown_warning",
    "metadata_json",
]

PAPER_SCENARIO_VALIDATION_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "status",
    "start_date",
    "end_date",
    "periods_count",
    "scenarios_count",
    "signal_sources_count",
    "positive_periods_pct",
    "mean_return",
    "mean_drawdown",
    "governance_status",
    "metadata_json",
]

PAPER_SCENARIO_VALIDATION_RESULT_COLUMNS = [
    "id",
    "run_id",
    "period_id",
    "scenario_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "total_return",
    "max_drawdown",
    "sharpe",
    "sortino",
    "win_rate",
    "profit_factor",
    "trades_count",
    "turnover",
    "cost_bps",
    "slippage_bps",
    "governance_status",
    "metadata_json",
]

PAPER_COST_SENSITIVITY_COLUMNS = [
    "id",
    "run_id",
    "cost_scenario",
    "cost_bps",
    "slippage_bps",
    "mean_return",
    "mean_drawdown",
    "positive_periods_pct",
    "cost_robustness_class",
    "metadata_json",
]

PAPER_SIGNAL_SOURCE_COMPARISON_COLUMNS = [
    "id",
    "run_id",
    "signal_source",
    "mean_return",
    "mean_drawdown",
    "win_rate",
    "profit_factor",
    "trades_count",
    "robustness_class",
    "metadata_json",
]

PAPER_FRAGILITY_RUN_COLUMNS = [
    "id",
    "created_at",
    "source_run_id",
    "status",
    "total_trades",
    "total_net_pnl",
    "fragility_score",
    "fragility_class",
    "governance_status",
    "metadata_json",
]

PAPER_FRAGILITY_ASSET_COLUMNS = [
    "id",
    "run_id",
    "ticker",
    "trades_count",
    "net_pnl",
    "win_rate",
    "contribution_pct",
    "cost_drag",
    "drawdown_contribution",
    "fragility_score",
    "fragility_class",
    "metadata_json",
]

PAPER_FRAGILITY_SIGNAL_SOURCE_COLUMNS = [
    "id",
    "run_id",
    "signal_source",
    "trades_count",
    "net_pnl",
    "win_rate",
    "contribution_pct",
    "cost_drag",
    "fragility_score",
    "fragility_class",
    "metadata_json",
]

PAPER_DRAWDOWN_PERIOD_COLUMNS = [
    "id",
    "run_id",
    "drawdown_start",
    "drawdown_trough",
    "drawdown_recovery",
    "depth",
    "duration_days",
    "recovered",
    "metadata_json",
]

PAPER_INVESTIGATION_RUN_COLUMNS = [
    "id",
    "created_at",
    "base_paper_run_id",
    "base_fragility_run_id",
    "hypotheses_count",
    "improved_count",
    "rejected_count",
    "observation_count",
    "best_hypothesis_id",
    "best_improvement_score",
    "metadata_json",
]

PAPER_INVESTIGATION_RESULT_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "hypothesis_type",
    "target",
    "title",
    "simulated_return",
    "simulated_drawdown",
    "simulated_trades",
    "simulated_win_rate",
    "simulated_profit_factor",
    "fragility_score_before",
    "fragility_score_after",
    "improvement_score",
    "governance_status",
    "conclusion",
    "metadata_json",
]

PAPER_HYPOTHESIS_OOS_RUN_COLUMNS = [
    "id",
    "created_at",
    "hypothesis_id",
    "hypothesis_type",
    "target",
    "windows_count",
    "scenarios_count",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "robustness_class",
    "governance_status",
    "metadata_json",
]

PAPER_HYPOTHESIS_OOS_RESULT_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "scenario_name",
    "signal_source",
    "start_date",
    "end_date",
    "base_return",
    "hypothesis_return",
    "return_delta",
    "base_drawdown",
    "hypothesis_drawdown",
    "drawdown_delta",
    "base_fragility_score",
    "hypothesis_fragility_score",
    "fragility_delta",
    "trades_count",
    "improvement_detected",
    "overfitting_flag",
    "cost_sensitivity_flag",
    "regime_instability_flag",
    "metadata_json",
]

PAPER_HYPOTHESIS_OOS_COVERAGE_COLUMNS = [
    "id",
    "run_id",
    "window_id",
    "scenario_name",
    "signal_source",
    "regime_filter",
    "start_date",
    "end_date",
    "signals_count",
    "price_days_count",
    "tickers_count",
    "useful_cell",
    "source_coverage_status",
    "message",
    "metadata_json",
]

SIGNAL_COVERAGE_RUN_COLUMNS = [
    "id",
    "created_at",
    "start_date",
    "end_date",
    "sources_checked",
    "coverage_status",
    "useful_cells_pct",
    "metadata_json",
]

SIGNAL_COVERAGE_BY_SOURCE_COLUMNS = [
    "id",
    "run_id",
    "signal_source",
    "signals_count",
    "tickers_count",
    "active_days_count",
    "regimes_count",
    "useful_cells_count",
    "coverage_pct",
    "coverage_status",
    "requirements_status",
    "metadata_json",
]

PAPER_HYPOTHESIS_RANKING_RUN_COLUMNS = [
    "id",
    "created_at",
    "hypotheses_count",
    "sources_count",
    "scenarios_count",
    "robust_count",
    "promising_count",
    "rejected_count",
    "best_hypothesis_id",
    "best_score",
    "metadata_json",
]

PAPER_HYPOTHESIS_RANKING_RESULT_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "signal_source",
    "scenario_name",
    "positive_improvement_pct",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "cost_sensitivity_flag",
    "overfitting_flag",
    "source_diversity_score",
    "hypothesis_robustness_score",
    "hypothesis_class",
    "governance_status",
    "metadata_json",
]

PAPER_HYPOTHESIS_DEEP_OOS_RUN_COLUMNS = [
    "id",
    "created_at",
    "hypotheses_count",
    "start_date",
    "end_date",
    "status",
    "best_hypothesis_id",
    "approved_count",
    "blocked_count",
    "metadata_json",
]

PAPER_HYPOTHESIS_DEEP_OOS_RESULT_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "signal_source",
    "cost_scenario",
    "slippage_scenario",
    "regime",
    "ticker",
    "windows_count",
    "trades_count",
    "mean_return_delta",
    "mean_drawdown_delta",
    "mean_fragility_delta",
    "positive_improvement_pct",
    "block_reason",
    "governance_status",
    "metadata_json",
]

PAPER_HYPOTHESIS_BLOCK_REASON_COLUMNS = [
    "id",
    "run_id",
    "hypothesis_id",
    "primary_block_reason",
    "secondary_block_reason",
    "explanation",
    "required_actions_json",
    "metadata_json",
]

ASSET_INTELLIGENCE_DIFF_COLUMNS = [
    "id",
    "created_at",
    "ticker",
    "previous_snapshot_id",
    "current_snapshot_id",
    "previous_created_at",
    "current_created_at",
    "changes_count",
    "changed_fields_json",
    "score_delta",
    "data_quality_delta",
    "status_changed",
    "governance_changed",
    "valuation_changed",
    "technical_changed",
    "quant_changed",
    "event_changed",
    "regime_changed",
    "options_changed",
    "material_change",
    "material_change_type",
    "explanation",
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


def load_data_source_audit_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "data_source_audit_runs",
        DATA_SOURCE_AUDIT_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_data_source_audit_results_for_dashboard(db_path: str | Path, run_id: int | None = None, limit: int = 200) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "data_source_audit_results",
        DATA_SOURCE_AUDIT_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
        limit=None if run_id is not None else limit,
    )


def load_data_source_traceability_for_dashboard(db_path: str | Path, ticker: str | None = None, limit: int = 500) -> pd.DataFrame:
    where = "ticker = ?" if ticker else ""
    params = (ticker,) if ticker else None
    return _read_table(
        db_path,
        "data_source_traceability",
        DATA_SOURCE_TRACEABILITY_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
        limit=limit,
    )


def load_data_file_manifest_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(db_path, "data_file_manifest_runs", DATA_FILE_MANIFEST_RUN_COLUMNS, order_by="id DESC", limit=limit)


def load_data_file_manifest_for_dashboard(db_path: str | Path, active_only: bool = True, limit: int = 500) -> pd.DataFrame:
    where = "active = 1" if active_only else ""
    return _read_table(db_path, "data_file_manifest", DATA_FILE_MANIFEST_COLUMNS, where=where, order_by="id DESC", limit=limit)


def load_data_reconciliation_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(db_path, "data_reconciliation_runs", DATA_RECONCILIATION_RUN_COLUMNS, order_by="id DESC", limit=limit)


def load_data_reconciliation_results_for_dashboard(db_path: str | Path, run_id: int | None = None, limit: int = 500) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "data_reconciliation_results", DATA_RECONCILIATION_RESULT_COLUMNS, where=where, params=params, order_by="id DESC", limit=None if run_id is not None else limit)


def load_ingestion_assistant_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(db_path, "ingestion_assistant_runs", INGESTION_ASSISTANT_RUN_COLUMNS, order_by="id DESC", limit=limit)


def load_ingestion_assistant_steps_for_dashboard(db_path: str | Path, run_id: int | None = None, limit: int = 200) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "ingestion_assistant_steps", INGESTION_ASSISTANT_STEP_COLUMNS, where=where, params=params, order_by="step_order", limit=None if run_id is not None else limit)


def load_post_ingestion_validation_for_dashboard(db_path: str | Path, run_id: int | None = None, limit: int = 200) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "post_ingestion_validation_results", POST_INGESTION_VALIDATION_COLUMNS, where=where, params=params, order_by="id DESC", limit=None if run_id is not None else limit)


def load_ingestion_comparison_for_dashboard(db_path: str | Path, run_id: int | None = None, limit: int = 200) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "ingestion_reliability_comparison", INGESTION_COMPARISON_COLUMNS, where=where, params=params, order_by="id DESC", limit=None if run_id is not None else limit)


def load_option_scanner_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "option_scanner_runs",
        OPTION_SCANNER_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_options_chain_snapshots_for_dashboard(db_path: str | Path, limit: int = 1000) -> pd.DataFrame:
    return _read_table(
        db_path,
        "options_chain_snapshots",
        OPTIONS_CHAIN_SNAPSHOT_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_option_structure_candidates_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "option_structure_candidates",
        OPTION_STRUCTURE_CANDIDATE_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_option_structure_backtest_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "option_structure_backtest_runs",
        OPTION_STRUCTURE_BACKTEST_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_option_structure_backtest_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "option_structure_backtest_results",
        OPTION_STRUCTURE_BACKTEST_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_option_walk_forward_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "option_walk_forward_runs",
        OPTION_WALK_FORWARD_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_option_walk_forward_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "option_walk_forward_results",
        OPTION_WALK_FORWARD_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_option_context_summary_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "option_context_summary",
        OPTION_CONTEXT_SUMMARY_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_technical_features_for_dashboard(db_path: str | Path, limit: int = 1000) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_feature_snapshots",
        TECHNICAL_FEATURE_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_technical_setups_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_setup_signals",
        TECHNICAL_SETUP_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_technical_backtest_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_backtest_runs",
        TECHNICAL_BACKTEST_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_technical_backtest_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "technical_backtest_results",
        TECHNICAL_BACKTEST_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="id DESC",
    )


def load_technical_walk_forward_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_walk_forward_runs",
        TECHNICAL_WALK_FORWARD_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_technical_walk_forward_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "technical_walk_forward_results",
        TECHNICAL_WALK_FORWARD_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="window_id",
    )


def load_technical_threshold_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_threshold_optimization_runs",
        TECHNICAL_THRESHOLD_OPTIMIZATION_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_technical_dedup_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "technical_setup_dedup_runs",
        TECHNICAL_SETUP_DEDUP_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_asset_intelligence_snapshots_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "asset_intelligence_snapshots",
        ASSET_INTELLIGENCE_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_asset_intelligence_diffs_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "asset_intelligence_diffs",
        ASSET_INTELLIGENCE_DIFF_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_volatility_estimates_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "volatility_estimates",
        VOLATILITY_ESTIMATE_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_risk_snapshots_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "risk_snapshots",
        RISK_SNAPSHOT_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_position_sizing_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "position_sizing_snapshots",
        POSITION_SIZING_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_stress_tests_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "stress_test_results",
        STRESS_TEST_RESULT_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_simulation_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_simulation_runs",
        PAPER_SIMULATION_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_paper_orders_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_orders", PAPER_ORDER_COLUMNS, where=where, params=params, order_by="id DESC")


def load_paper_positions_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_positions", PAPER_POSITION_COLUMNS, where=where, params=params, order_by="id DESC")


def load_paper_equity_curve_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_equity_curve", PAPER_EQUITY_COLUMNS, where=where, params=params, order_by="trade_date")


def load_paper_exit_events_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_exit_events", PAPER_EXIT_EVENT_COLUMNS, where=where, params=params, order_by="id DESC")


def load_paper_rebalance_events_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_rebalance_events", PAPER_REBALANCE_EVENT_COLUMNS, where=where, params=params, order_by="id DESC")


def load_paper_pnl_attribution_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(db_path, "paper_pnl_attribution", PAPER_PNL_ATTRIBUTION_COLUMNS, where=where, params=params, order_by="id DESC")


def load_paper_simulation_comparisons_for_dashboard(db_path: str | Path, limit: int = 500) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_simulation_comparisons",
        PAPER_SIMULATION_COMPARISON_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_exit_optimization_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_exit_optimization_runs",
        PAPER_EXIT_OPTIMIZATION_RUN_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_exit_optimization_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_exit_optimization_results",
        PAPER_EXIT_OPTIMIZATION_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="score_objective DESC, id DESC",
    )


def load_paper_walk_forward_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_walk_forward_runs",
        PAPER_WALK_FORWARD_RUN_COLUMNS,
        order_by="started_at DESC, id DESC",
        limit=limit,
    )


def load_paper_walk_forward_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_walk_forward_results",
        PAPER_WALK_FORWARD_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="window_id",
    )


def load_paper_scenario_validation_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_scenario_validation_runs",
        PAPER_SCENARIO_VALIDATION_RUN_COLUMNS,
        order_by="started_at DESC, id DESC",
        limit=limit,
    )


def load_paper_scenario_validation_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_scenario_validation_results",
        PAPER_SCENARIO_VALIDATION_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="period_id, scenario_id",
    )


def load_paper_cost_sensitivity_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_cost_sensitivity_results",
        PAPER_COST_SENSITIVITY_COLUMNS,
        where=where,
        params=params,
        order_by="cost_bps, slippage_bps",
    )


def load_paper_signal_source_comparison_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_signal_source_comparison",
        PAPER_SIGNAL_SOURCE_COMPARISON_COLUMNS,
        where=where,
        params=params,
        order_by="mean_return DESC",
    )


def load_paper_fragility_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_fragility_runs",
        PAPER_FRAGILITY_RUN_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_fragility_by_asset_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_fragility_by_asset",
        PAPER_FRAGILITY_ASSET_COLUMNS,
        where=where,
        params=params,
        order_by="fragility_score DESC, id DESC",
    )


def load_paper_fragility_by_signal_source_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_fragility_by_signal_source",
        PAPER_FRAGILITY_SIGNAL_SOURCE_COLUMNS,
        where=where,
        params=params,
        order_by="fragility_score DESC, id DESC",
    )


def load_paper_drawdown_periods_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_drawdown_periods",
        PAPER_DRAWDOWN_PERIOD_COLUMNS,
        where=where,
        params=params,
        order_by="depth ASC, id DESC",
    )


def load_paper_investigation_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_investigation_runs",
        PAPER_INVESTIGATION_RUN_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_investigation_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_investigation_results",
        PAPER_INVESTIGATION_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="improvement_score DESC, id DESC",
    )


def load_paper_hypothesis_oos_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_hypothesis_oos_runs",
        PAPER_HYPOTHESIS_OOS_RUN_COLUMNS,
        order_by="created_at DESC, id DESC",
        limit=limit,
    )


def load_paper_hypothesis_oos_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_hypothesis_oos_results",
        PAPER_HYPOTHESIS_OOS_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="window_id, scenario_name",
    )


def load_paper_hypothesis_oos_coverage_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_hypothesis_oos_coverage",
        PAPER_HYPOTHESIS_OOS_COVERAGE_COLUMNS,
        where=where,
        params=params,
        order_by="window_id, scenario_name",
    )


def load_signal_coverage_runs_for_dashboard(db_path: str | Path, limit: int = 20) -> pd.DataFrame:
    return _read_table(
        db_path,
        "signal_coverage_runs",
        SIGNAL_COVERAGE_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_signal_coverage_by_source_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "signal_coverage_by_source",
        SIGNAL_COVERAGE_BY_SOURCE_COLUMNS,
        where=where,
        params=params,
        order_by="signal_source",
    )


def load_paper_hypothesis_ranking_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_hypothesis_ranking_runs",
        PAPER_HYPOTHESIS_RANKING_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_paper_hypothesis_ranking_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_hypothesis_ranking_results",
        PAPER_HYPOTHESIS_RANKING_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="hypothesis_robustness_score DESC, id DESC",
    )


def load_paper_hypothesis_deep_oos_runs_for_dashboard(db_path: str | Path, limit: int = 50) -> pd.DataFrame:
    return _read_table(
        db_path,
        "paper_hypothesis_deep_oos_runs",
        PAPER_HYPOTHESIS_DEEP_OOS_RUN_COLUMNS,
        order_by="id DESC",
        limit=limit,
    )


def load_paper_hypothesis_deep_oos_results_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_hypothesis_deep_oos_results",
        PAPER_HYPOTHESIS_DEEP_OOS_RESULT_COLUMNS,
        where=where,
        params=params,
        order_by="hypothesis_id, signal_source, cost_scenario, slippage_scenario, regime, ticker",
    )


def load_paper_hypothesis_block_reasons_for_dashboard(db_path: str | Path, run_id: int | None = None) -> pd.DataFrame:
    where = "run_id = ?" if run_id is not None else ""
    params = (int(run_id),) if run_id is not None else None
    return _read_table(
        db_path,
        "paper_hypothesis_block_reasons",
        PAPER_HYPOTHESIS_BLOCK_REASON_COLUMNS,
        where=where,
        params=params,
        order_by="hypothesis_id",
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
