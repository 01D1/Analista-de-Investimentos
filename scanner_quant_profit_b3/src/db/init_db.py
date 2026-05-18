import sqlite3
from pathlib import Path

from src.utils import load_config, project_path


REALTIME_SIGNAL_EXTRA_COLUMNS = {
    "score_final": "REAL",
    "score_momentum": "REAL",
    "score_tendencia": "REAL",
    "score_liquidez": "REAL",
    "score_volatilidade": "REAL",
    "score_risco": "REAL",
    "signal_type": "TEXT",
    "signal_confidence": "TEXT",
    "explanation": "TEXT",
}

HISTORICAL_BACKTEST_RESULT_EXTRA_COLUMNS = {
    "score_momentum": "REAL",
    "score_tendencia": "REAL",
    "score_liquidez": "REAL",
    "score_volatilidade": "REAL",
    "score_risco": "REAL",
    "net_return_1d": "REAL",
    "net_return_3d": "REAL",
    "net_return_5d": "REAL",
    "net_return_10d": "REAL",
    "execution_quality": "TEXT",
    "liquidity_penalty": "REAL",
    "total_cost_pct": "REAL",
    "total_slippage_pct": "REAL",
    "is_tradeable": "INTEGER",
    "volume": "REAL",
    "trades": "REAL",
    "signal_quality": "TEXT",
    "estimated_capacity": "REAL",
    "capacity_class": "TEXT",
    "primary_regime": "TEXT",
    "trend_regime": "TEXT",
    "volatility_regime": "TEXT",
    "liquidity_regime": "TEXT",
    "risk_regime": "TEXT",
    "regime_confidence": "REAL",
    "explanation": "TEXT",
    "market_regime": "TEXT",
    "has_event": "INTEGER",
    "event_type": "TEXT",
    "event_impact_score": "REAL",
    "event_context_type": "TEXT",
    "days_from_event": "INTEGER",
    "event_title": "TEXT",
    "impact_direction": "TEXT",
}

HISTORICAL_BACKTEST_RUN_EXTRA_COLUMNS = {
    "net_mode": "INTEGER",
    "cost_bps": "REAL",
    "slippage_bps": "REAL",
    "min_volume": "REAL",
    "only_tradeable": "INTEGER",
    "mean_net_return_1d": "REAL",
    "mean_net_return_3d": "REAL",
    "mean_net_return_5d": "REAL",
    "mean_net_return_10d": "REAL",
    "net_hit_rate_1d": "REAL",
    "net_hit_rate_3d": "REAL",
    "net_hit_rate_5d": "REAL",
    "net_hit_rate_10d": "REAL",
}

GOVERNANCE_REVIEW_EXTRA_COLUMNS = {
    "regime_status": "TEXT",
    "allowed_regimes_json": "TEXT",
    "blocked_regimes_json": "TEXT",
    "event_status": "TEXT",
    "allowed_event_contexts_json": "TEXT",
    "blocked_event_contexts_json": "TEXT",
}

MARKET_EVENT_EXTRA_COLUMNS = {
    "duplicate_group_id": "TEXT",
    "is_duplicate": "INTEGER",
    "canonical_event_id": "TEXT",
    "coverage_source": "TEXT",
    "normalized_at": "TEXT",
}

ASSET_INTELLIGENCE_EXTRA_COLUMNS = {
    "subsector": "TEXT",
    "technical_setup_score": "REAL",
    "technical_setup_confidence": "REAL",
    "technical_oos_status": "TEXT",
    "technical_explanation": "TEXT",
    "quant_signal_confidence": "TEXT",
    "quant_explanation": "TEXT",
    "valuation_method": "TEXT",
    "fundamental_quality_score": "REAL",
    "financial_health_score": "REAL",
    "profitability_score": "REAL",
    "growth_score": "REAL",
    "leverage_score": "REAL",
    "valuation_governance_status": "TEXT",
    "event_impact_score": "REAL",
    "event_coverage_quality": "TEXT",
    "risk_regime": "TEXT",
    "regime_governance_status": "TEXT",
    "option_liquidity_score": "REAL",
    "option_execution_quality": "TEXT",
    "option_explanation": "TEXT",
    "ensemble_vol": "REAL",
    "var_95": "REAL",
    "expected_shortfall_95": "REAL",
    "recommended_size": "REAL",
    "recommended_position_value": "REAL",
    "risk_status": "TEXT",
    "risk_limiting_factor": "TEXT",
    "risk_explanation": "TEXT",
    "governance_blocked": "INTEGER",
}


def _ensure_columns(cur: sqlite3.Cursor, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, sql_type in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def _create_b3_quotes_view(cur: sqlite3.Cursor) -> None:
    cur.execute("""
    CREATE VIEW b3_quotes AS
    SELECT
        trade_date,
        ticker,
        market_type,
        company_name,
        open,
        high,
        low,
        average,
        close,
        best_bid,
        best_ask,
        trades,
        quantity,
        volume,
        strike            AS option_exercise_price,
        expiration_date   AS option_maturity,
        CASE
            WHEN option_type IN ('CALL', 'PUT') THEN option_type
            WHEN market_type IN ('010', '10', 10) THEN 'ACAO'
            ELSE 'OUTRO'
        END               AS asset_type
    FROM cotahist_daily
    WHERE option_type IN ('CALL', 'PUT') OR market_type IN ('010', '10', 10)
    """)


def init_database(db_path: str | Path, verbose: bool = True) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profit_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_at TEXT NOT NULL,
        asset TEXT NOT NULL,
        trade_date TEXT,
        trade_time TEXT,
        last REAL,
        open REAL,
        high REAL,
        low REAL,
        prev_close REAL,
        variation_pct REAL,
        variation_pts REAL,
        trades INTEGER,
        quantity REAL,
        volume REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cotahist_daily (
        trade_date TEXT NOT NULL,
        ticker TEXT NOT NULL,
        market_type TEXT,
        bdi_code TEXT,
        company_name TEXT,
        specification TEXT,
        term_days TEXT,
        open REAL,
        high REAL,
        low REAL,
        average REAL,
        close REAL,
        best_bid REAL,
        best_ask REAL,
        trades INTEGER,
        quantity REAL,
        volume REAL,
        strike REAL,
        option_type TEXT,
        expiration_date TEXT,
        source_year INTEGER,
        PRIMARY KEY (trade_date, ticker, market_type)
    )
    """)
    _ensure_columns(
        cur,
        "cotahist_daily",
        {
            "market_type": "TEXT",
            "bdi_code": "TEXT",
            "company_name": "TEXT",
            "specification": "TEXT",
            "term_days": "TEXT",
            "open": "REAL",
            "high": "REAL",
            "low": "REAL",
            "average": "REAL",
            "best_bid": "REAL",
            "best_ask": "REAL",
            "trades": "INTEGER",
            "quantity": "REAL",
            "volume": "REAL",
            "strike": "REAL",
            "option_type": "TEXT",
            "expiration_date": "TEXT",
            "source_year": "INTEGER",
        },
    )

    cur.execute("""
    CREATE TABLE IF NOT EXISTS realtime_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_at TEXT NOT NULL,
        asset TEXT NOT NULL,
        last REAL,
        variation_pct REAL,
        volume REAL,
        trades INTEGER,
        score INTEGER,
        signal TEXT,
        motivos TEXT
    )
    """)
    _ensure_columns(cur, "realtime_signals", REALTIME_SIGNAL_EXTRA_COLUMNS)

    # View de compatibilidade para combined_stock_options_scanner.
    # Só é criada se b3_quotes ainda não existir como TABLE (caso já exista
    # como tabela real, é preservada para não perder dados do coletor legado).
    existing = cur.execute(
        "SELECT type FROM sqlite_master WHERE name='b3_quotes'"
    ).fetchone()
    if existing is None:
        _create_b3_quotes_view(cur)
    elif existing[0] == 'view':
        cur.execute("DROP VIEW b3_quotes")
        _create_b3_quotes_view(cur)

    # Diário de trades
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trade_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_sinal TEXT,
        ativo TEXT,
        opcao TEXT,
        tipo TEXT,
        direcao TEXT,
        entrada_planejada REAL,
        preco_entrada REAL,
        stop REAL,
        alvo_1 REAL,
        alvo_2 REAL,
        quantidade INTEGER,
        risco_financeiro REAL,
        status TEXT DEFAULT 'AGUARDAR_ENTRADA',
        resultado REAL,
        retorno_pct REAL,
        observacoes TEXT
    )
    """)

    # Greeks completos + IV implícita por opção por data
    cur.execute("""
    CREATE TABLE IF NOT EXISTS options_greeks_snapshot (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_at  TEXT NOT NULL,
        trade_date   TEXT NOT NULL,
        underlying   TEXT NOT NULL,
        ticker       TEXT NOT NULL,
        option_type  TEXT NOT NULL,
        strike       REAL,
        expiry       TEXT,
        dte          INTEGER,
        price        REAL,
        volume       REAL,
        trades       INTEGER,
        liq_score    REAL,
        moneyness    TEXT,
        moneyness_pct REAL,
        -- Volatilidade
        iv_implied   REAL,
        iv_hv        REAL,
        iv_vs_hv     REAL,
        -- Greeks 1ª ordem
        delta        REAL,
        rho          REAL,
        -- Greeks 2ª ordem
        gamma        REAL,
        theta        REAL,
        vega         REAL,
        vanna        REAL,
        charm        REAL,
        -- Greeks 3ª ordem
        vomma        REAL,
        speed        REAL,
        -- Decomposição de preço
        intrinsic_value REAL,
        time_value      REAL,
        stock_price     REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS score_calibration_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        source TEXT,
        total_assets INTEGER,
        mean_score_final REAL,
        median_score_final REAL,
        std_score_final REAL,
        min_score_final REAL,
        max_score_final REAL,
        p10_score_final REAL,
        p25_score_final REAL,
        p50_score_final REAL,
        p75_score_final REAL,
        p90_score_final REAL,
        count_0_20 INTEGER,
        count_20_40 INTEGER,
        count_40_60 INTEGER,
        count_60_80 INTEGER,
        count_80_100 INTEGER,
        inflation_alert INTEGER,
        inflation_message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS score_calibration_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        captured_at TEXT,
        asset TEXT,
        legacy_score REAL,
        score_final REAL,
        score_momentum REAL,
        score_tendencia REAL,
        score_liquidez REAL,
        score_volatilidade REAL,
        score_risco REAL,
        legacy_signal TEXT,
        signal_type TEXT,
        signal_confidence TEXT,
        divergence_type TEXT,
        ranking_legacy INTEGER,
        ranking_new INTEGER,
        ranking_change INTEGER,
        explanation TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS historical_backtest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        tickers_count INTEGER,
        signals_count INTEGER,
        horizons TEXT,
        mean_return_1d REAL,
        mean_return_3d REAL,
        mean_return_5d REAL,
        mean_return_10d REAL,
        hit_rate_1d REAL,
        hit_rate_3d REAL,
        hit_rate_5d REAL,
        hit_rate_10d REAL,
        net_mode INTEGER,
        cost_bps REAL,
        slippage_bps REAL,
        min_volume REAL,
        only_tradeable INTEGER,
        mean_net_return_1d REAL,
        mean_net_return_3d REAL,
        mean_net_return_5d REAL,
        mean_net_return_10d REAL,
        net_hit_rate_1d REAL,
        net_hit_rate_3d REAL,
        net_hit_rate_5d REAL,
        net_hit_rate_10d REAL,
        metadata_json TEXT
    )
    """)
    _ensure_columns(cur, "historical_backtest_runs", HISTORICAL_BACKTEST_RUN_EXTRA_COLUMNS)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS historical_backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        ticker TEXT,
        score_final REAL,
        score_momentum REAL,
        score_tendencia REAL,
        score_liquidez REAL,
        score_volatilidade REAL,
        score_risco REAL,
        signal_type TEXT,
        signal_confidence TEXT,
        future_return_1d REAL,
        future_return_3d REAL,
        future_return_5d REAL,
        future_return_10d REAL,
        net_return_1d REAL,
        net_return_3d REAL,
        net_return_5d REAL,
        net_return_10d REAL,
        mfe_5d REAL,
        mae_5d REAL,
        score_bucket TEXT,
        execution_quality TEXT,
        liquidity_penalty REAL,
        total_cost_pct REAL,
        total_slippage_pct REAL,
        is_tradeable INTEGER,
        volume REAL,
        trades REAL,
        signal_quality TEXT,
        estimated_capacity REAL,
        capacity_class TEXT,
        primary_regime TEXT,
        trend_regime TEXT,
        volatility_regime TEXT,
        liquidity_regime TEXT,
        risk_regime TEXT,
        regime_confidence REAL,
        explanation TEXT,
        market_regime TEXT,
        has_event INTEGER,
        event_type TEXT,
        event_impact_score REAL,
        event_context_type TEXT,
        days_from_event INTEGER,
        event_title TEXT,
        impact_direction TEXT,
        metadata_json TEXT
    )
    """)
    _ensure_columns(cur, "historical_backtest_results", HISTORICAL_BACKTEST_RESULT_EXTRA_COLUMNS)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT,
        event_datetime TEXT,
        ticker TEXT,
        related_tickers TEXT,
        company_name TEXT,
        event_type TEXT,
        event_source TEXT,
        event_title TEXT,
        event_summary TEXT,
        event_url TEXT,
        sector TEXT,
        macro_tag TEXT,
        commodity_tag TEXT,
        impact_direction TEXT,
        impact_score REAL,
        confidence REAL,
        created_at TEXT,
        duplicate_group_id TEXT,
        is_duplicate INTEGER,
        canonical_event_id TEXT,
        coverage_source TEXT,
        normalized_at TEXT,
        metadata_json TEXT
    )
    """)
    _ensure_columns(cur, "market_events", MARKET_EVENT_EXTRA_COLUMNS)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_event_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        backtest_result_id INTEGER,
        ticker TEXT,
        signal_date TEXT,
        event_id INTEGER,
        event_date TEXT,
        event_type TEXT,
        event_impact_score REAL,
        days_from_event INTEGER,
        link_type TEXT,
        confidence REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_context_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        start_date TEXT,
        end_date TEXT,
        events_count INTEGER,
        signals_linked INTEGER,
        tickers_count INTEGER,
        source TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_coverage_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        start_date TEXT,
        end_date TEXT,
        sources TEXT,
        events_loaded INTEGER,
        events_after_dedup INTEGER,
        tickers_count INTEGER,
        signals_count INTEGER,
        signals_with_event_pct REAL,
        tickers_with_event_pct REAL,
        coverage_quality TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS event_coverage_by_regime (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coverage_run_id INTEGER,
        regime_type TEXT,
        regime_value TEXT,
        signals_count INTEGER,
        signals_with_event INTEGER,
        signals_without_event INTEGER,
        signals_with_event_pct REAL,
        dominant_event_type TEXT,
        dominant_event_source TEXT,
        coverage_quality TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS options_chain_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_at TEXT,
        trade_date TEXT,
        option_ticker TEXT,
        underlying TEXT,
        option_type TEXT,
        strike REAL,
        maturity_date TEXT,
        days_to_maturity INTEGER,
        last_price REAL,
        bid REAL,
        ask REAL,
        spread_pct REAL,
        volume REAL,
        trades REAL,
        financial_volume REAL,
        open_interest REAL,
        underlying_price REAL,
        moneyness_pct REAL,
        moneyness_class TEXT,
        intrinsic_value REAL,
        extrinsic_value REAL,
        breakeven REAL,
        implied_volatility REAL,
        historical_volatility REAL,
        delta REAL,
        gamma REAL,
        theta REAL,
        vega REAL,
        liquidity_score REAL,
        risk_score REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_structure_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        structure_type TEXT,
        underlying TEXT,
        maturity_date TEXT,
        legs_json TEXT,
        net_debit REAL,
        net_credit REAL,
        max_profit REAL,
        max_loss REAL,
        breakeven REAL,
        payoff_ratio REAL,
        liquidity_score REAL,
        risk_score REAL,
        structure_score REAL,
        candidate_status TEXT,
        explanation TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_scanner_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        options_count INTEGER,
        structures_count INTEGER,
        approved_for_study_count INTEGER,
        blocked_count INTEGER,
        warning_count INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_structure_backtest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        underlyings TEXT,
        structure_type TEXT,
        entries_count INTEGER,
        completed_count INTEGER,
        skipped_count INTEGER,
        mean_net_return REAL,
        win_rate REAL,
        profit_factor REAL,
        avg_cost_drag REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_structure_backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        entry_date TEXT,
        exit_date TEXT,
        underlying TEXT,
        structure_type TEXT,
        maturity_date TEXT,
        dte_entry INTEGER,
        dte_exit INTEGER,
        legs_json TEXT,
        entry_debit REAL,
        entry_credit REAL,
        exit_value REAL,
        gross_pnl REAL,
        net_pnl REAL,
        gross_return REAL,
        net_return REAL,
        max_loss REAL,
        return_on_risk REAL,
        exit_reason TEXT,
        liquidity_score REAL,
        spread_cost REAL,
        transaction_cost REAL,
        slippage_cost REAL,
        execution_quality TEXT,
        status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_walk_forward_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        structure_type TEXT,
        train_months INTEGER,
        test_months INTEGER,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_test_net_return REAL,
        mean_test_win_rate REAL,
        mean_test_profit_factor REAL,
        robustness_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_walk_forward_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        train_start TEXT,
        train_end TEXT,
        test_start TEXT,
        test_end TEXT,
        train_trades INTEGER,
        test_trades INTEGER,
        train_mean_net_return REAL,
        test_mean_net_return REAL,
        train_win_rate REAL,
        test_win_rate REAL,
        train_profit_factor REAL,
        test_profit_factor REAL,
        avg_cost_drag REAL,
        skipped_pct REAL,
        positive_test_window INTEGER,
        overfitting_flag INTEGER,
        insufficient_data_flag INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS option_context_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        context_type TEXT,
        context_value TEXT,
        trades INTEGER,
        mean_net_return REAL,
        win_rate REAL,
        profit_factor REAL,
        avg_cost_drag REAL,
        skipped_pct REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_feature_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        trend_score REAL,
        momentum_score REAL,
        volatility_score REAL,
        volume_score REAL,
        breakout_score REAL,
        support_resistance_score REAL,
        pattern_score REAL,
        risk_score REAL,
        technical_score_final REAL,
        technical_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_setup_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        setup_type TEXT,
        setup_score REAL,
        setup_confidence REAL,
        setup_direction TEXT,
        trigger_price REAL,
        invalidation_price REAL,
        target_hint REAL,
        risk_hint REAL,
        technical_status TEXT,
        governance_status TEXT,
        explanation TEXT,
        reasons_for_json TEXT,
        reasons_against_json TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_backtest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        setup_type TEXT,
        start_date TEXT,
        end_date TEXT,
        signals_count INTEGER,
        mean_return_5d REAL,
        hit_rate_5d REAL,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        ticker TEXT,
        setup_type TEXT,
        technical_score_final REAL,
        technical_status TEXT,
        future_return_1d REAL,
        future_return_3d REAL,
        future_return_5d REAL,
        future_return_10d REAL,
        hit_1d INTEGER,
        hit_3d INTEGER,
        hit_5d INTEGER,
        hit_10d INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_walk_forward_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        train_months INTEGER,
        test_months INTEGER,
        setup_type TEXT,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_test_return REAL,
        mean_test_hit_rate REAL,
        robustness_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_walk_forward_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        train_start TEXT,
        train_end TEXT,
        test_start TEXT,
        test_end TEXT,
        setup_type TEXT,
        best_params_json TEXT,
        train_signals INTEGER,
        test_signals INTEGER,
        train_mean_return REAL,
        test_mean_return REAL,
        train_hit_rate REAL,
        test_hit_rate REAL,
        test_positive INTEGER,
        overfitting_flag INTEGER,
        insufficient_data_flag INTEGER,
        concentration_warning INTEGER,
        stability_warning INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_threshold_optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        start_date TEXT,
        end_date TEXT,
        objective TEXT,
        best_params_json TEXT,
        best_mean_return REAL,
        best_hit_rate REAL,
        best_samples INTEGER,
        overfitting_warning TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS technical_setup_dedup_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        signals_before INTEGER,
        signals_after INTEGER,
        removed_count INTEGER,
        removed_pct REAL,
        top_redundant_setups_json TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS source_health_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checked_at TEXT,
        source_name TEXT,
        status TEXT,
        available INTEGER,
        records_count INTEGER,
        latest_date TEXT,
        age_days REAL,
        coverage_hint TEXT,
        path TEXT,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_routine_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        sources TEXT,
        health_overall_status TEXT,
        event_coverage_quality TEXT,
        events_loaded INTEGER,
        events_after_dedup INTEGER,
        signals_covered_pct REAL,
        governance_status TEXT,
        alerts_count INTEGER,
        report_path TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        alert_type TEXT,
        severity TEXT,
        title TEXT,
        message TEXT,
        source TEXT,
        resolved INTEGER DEFAULT 0,
        resolved_at TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS source_sla_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        window_days INTEGER,
        source_name TEXT,
        total_checks INTEGER,
        availability_pct REAL,
        ok_pct REAL,
        warning_pct REAL,
        error_pct REAL,
        missing_pct REAL,
        stale_pct REAL,
        avg_age_days REAL,
        max_age_days REAL,
        latest_status TEXT,
        last_ok_at TEXT,
        days_since_last_ok REAL,
        reliability_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS operational_observability_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        window_days INTEGER,
        overall_status TEXT,
        overall_availability_pct REAL,
        total_sources INTEGER,
        critical_sources INTEGER,
        total_alerts INTEGER,
        critical_alerts INTEGER,
        open_alerts INTEGER,
        routine_success_rate_pct REAL,
        routine_failure_rate_pct REAL,
        avg_signals_covered_pct REAL,
        coverage_trend_direction TEXT,
        summary_text TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS retention_cleanup_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        dry_run INTEGER,
        status TEXT,
        tables_evaluated INTEGER,
        rows_candidates INTEGER,
        rows_archived INTEGER,
        rows_deleted INTEGER,
        archive_dir TEXT,
        warnings_count INTEGER,
        errors_count INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS retention_cleanup_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        table_name TEXT,
        cutoff_date TEXT,
        rows_total INTEGER,
        rows_to_delete INTEGER,
        rows_archived INTEGER,
        rows_deleted INTEGER,
        protected INTEGER,
        status TEXT,
        archive_path TEXT,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_intelligence_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        company_name TEXT,
        sector TEXT,
        subsector TEXT,
        market_price REAL,
        technical_score_final REAL,
        technical_status TEXT,
        top_technical_setup TEXT,
        technical_setup_score REAL,
        technical_setup_confidence REAL,
        technical_governance_status TEXT,
        technical_oos_status TEXT,
        technical_explanation TEXT,
        quant_score REAL,
        quant_signal_type TEXT,
        quant_signal_confidence TEXT,
        quant_governance_status TEXT,
        quant_explanation TEXT,
        valuation_available INTEGER,
        fair_value REAL,
        upside_pct REAL,
        valuation_method TEXT,
        valuation_confidence REAL,
        fundamental_quality_score REAL,
        financial_health_score REAL,
        profitability_score REAL,
        growth_score REAL,
        leverage_score REAL,
        valuation_governance_status TEXT,
        has_recent_event INTEGER,
        event_type TEXT,
        event_context_type TEXT,
        event_impact_score REAL,
        event_coverage_quality TEXT,
        event_governance_status TEXT,
        primary_regime TEXT,
        trend_regime TEXT,
        volatility_regime TEXT,
        liquidity_regime TEXT,
        risk_regime TEXT,
        regime_governance_status TEXT,
        option_available INTEGER,
        best_option_structure_type TEXT,
        option_structure_score REAL,
        option_oos_governance_status TEXT,
        option_liquidity_score REAL,
        option_execution_quality TEXT,
        option_explanation TEXT,
        ensemble_vol REAL,
        var_95 REAL,
        expected_shortfall_95 REAL,
        recommended_size REAL,
        recommended_position_value REAL,
        risk_status TEXT,
        risk_limiting_factor TEXT,
        risk_explanation TEXT,
        integrated_score REAL,
        integrated_status TEXT,
        integrated_confidence TEXT,
        integrated_governance_status TEXT,
        data_quality_score REAL,
        governance_blocked INTEGER,
        explanation TEXT,
        reasons_for_json TEXT,
        reasons_against_json TEXT,
        required_actions_json TEXT,
        metadata_json TEXT
    )
    """)
    _ensure_columns(cur, "asset_intelligence_snapshots", ASSET_INTELLIGENCE_EXTRA_COLUMNS)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_intelligence_diffs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticker TEXT,
        previous_snapshot_id INTEGER,
        current_snapshot_id INTEGER,
        previous_created_at TEXT,
        current_created_at TEXT,
        changes_count INTEGER,
        changed_fields_json TEXT,
        score_delta REAL,
        data_quality_delta REAL,
        status_changed INTEGER,
        governance_changed INTEGER,
        valuation_changed INTEGER,
        technical_changed INTEGER,
        quant_changed INTEGER,
        event_changed INTEGER,
        regime_changed INTEGER,
        options_changed INTEGER,
        material_change INTEGER,
        material_change_type TEXT,
        explanation TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_source_audit_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        sources_checked INTEGER,
        ok_count INTEGER,
        warning_count INTEGER,
        error_count INTEGER,
        missing_count INTEGER,
        overall_reliability_score REAL,
        overall_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_source_audit_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_name TEXT,
        source_type TEXT,
        primary_or_secondary TEXT,
        available INTEGER,
        records_count INTEGER,
        latest_date TEXT,
        tickers_count INTEGER,
        coverage_scope TEXT,
        status TEXT,
        reliability_score REAL,
        reliability_class TEXT,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_source_traceability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticker TEXT,
        data_domain TEXT,
        source_name TEXT,
        source_type TEXT,
        source_url_or_path TEXT,
        source_date TEXT,
        collected_at TEXT,
        record_count INTEGER,
        checksum TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_file_manifest (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        file_path TEXT,
        file_name TEXT,
        extension TEXT,
        size_bytes INTEGER,
        modified_at TEXT,
        checksum TEXT,
        source_domain TEXT,
        active INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_file_manifest_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        files_count INTEGER,
        new_files_count INTEGER,
        changed_files_count INTEGER,
        removed_files_count INTEGER,
        status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_reconciliation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        reconciliation_type TEXT,
        status TEXT,
        issues_count INTEGER,
        fixes_suggested_count INTEGER,
        fixes_executed_count INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_reconciliation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_domain TEXT,
        issue_type TEXT,
        severity TEXT,
        status TEXT,
        description TEXT,
        suggested_command TEXT,
        executed INTEGER,
        execution_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_assistant_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        dry_run INTEGER,
        executed INTEGER,
        status TEXT,
        sources TEXT,
        steps_total INTEGER,
        steps_executed INTEGER,
        steps_failed INTEGER,
        manual_steps INTEGER,
        improvements_count INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_assistant_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        step_id TEXT,
        step_order INTEGER,
        source_domain TEXT,
        step_type TEXT,
        title TEXT,
        suggested_command TEXT,
        can_execute INTEGER,
        requires_confirm INTEGER,
        risk_level TEXT,
        status TEXT,
        stdout TEXT,
        stderr TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS post_ingestion_validation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_domain TEXT,
        validation_status TEXT,
        before_status TEXT,
        after_status TEXT,
        improvement_detected INTEGER,
        records_before INTEGER,
        records_after INTEGER,
        latest_date_before TEXT,
        latest_date_after TEXT,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_reliability_comparison (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        source_name TEXT,
        before_score REAL,
        after_score REAL,
        score_delta REAL,
        before_status TEXT,
        after_status TEXT,
        status_improved INTEGER,
        records_delta INTEGER,
        freshness_improved INTEGER,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS volatility_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        vol_5d REAL,
        vol_10d REAL,
        vol_20d REAL,
        vol_60d REAL,
        vol_252d REAL,
        vol_ewma REAL,
        downside_vol REAL,
        parkinson_vol REAL,
        garman_klass_vol REAL,
        atr_vol REAL,
        ensemble_vol REAL,
        volatility_regime TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        price REAL,
        position_value REAL,
        ensemble_vol REAL,
        volatility_regime TEXT,
        parametric_var_95 REAL,
        historical_var_95 REAL,
        expected_shortfall_95 REAL,
        recommended_size REAL,
        recommended_position_value REAL,
        limiting_factor TEXT,
        risk_status TEXT,
        explanation TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS var_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        position_value REAL,
        confidence REAL,
        horizon_days INTEGER,
        parametric_var REAL,
        historical_var REAL,
        modified_var REAL,
        expected_shortfall REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS position_sizing_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        capital REAL,
        risk_pct REAL,
        entry_price REAL,
        stop_price REAL,
        atr REAL,
        volatility REAL,
        avg_financial_volume REAL,
        size_fixed_risk REAL,
        size_atr REAL,
        size_var REAL,
        size_liquidity REAL,
        final_size REAL,
        final_position_value REAL,
        limiting_factor TEXT,
        estimated_var REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stress_test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticker TEXT,
        scenario TEXT,
        position_value REAL,
        estimated_loss REAL,
        loss_pct REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_governance_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        ticker TEXT,
        risk_status TEXT,
        risk_level TEXT,
        confidence_level TEXT,
        reasons_for_json TEXT,
        reasons_against_json TEXT,
        required_actions_json TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_simulation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        capital_initial REAL,
        capital_final REAL,
        total_return REAL,
        sharpe REAL,
        sortino REAL,
        max_drawdown REAL,
        trades_count INTEGER,
        win_rate REAL,
        profit_factor REAL,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        created_at TEXT,
        trade_date TEXT,
        ticker TEXT,
        side TEXT,
        quantity REAL,
        theoretical_price REAL,
        simulated_execution_price REAL,
        execution_cost REAL,
        slippage_cost REAL,
        order_status TEXT,
        signal_source TEXT,
        rejection_reason TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        ticker TEXT,
        quantity REAL,
        avg_price REAL,
        market_price REAL,
        market_value REAL,
        unrealized_pnl REAL,
        realized_pnl REAL,
        var_95 REAL,
        expected_shortfall_95 REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_equity_curve (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        cash REAL,
        equity REAL,
        exposure REAL,
        daily_return REAL,
        drawdown REAL,
        portfolio_var_95 REAL,
        portfolio_es_95 REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_exit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        ticker TEXT,
        position_id TEXT,
        exit_rule_triggered TEXT,
        exit_reason TEXT,
        exit_price REAL,
        pnl REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_rebalance_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        trade_date TEXT,
        ticker TEXT,
        action TEXT,
        current_weight REAL,
        target_weight REAL,
        order_quantity REAL,
        reason TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_pnl_attribution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        attribution_type TEXT,
        bucket TEXT,
        trades INTEGER,
        gross_pnl REAL,
        net_pnl REAL,
        win_rate REAL,
        avg_return REAL,
        contribution_pct REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_simulation_comparisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        simple_run_id INTEGER,
        advanced_run_id INTEGER,
        metric TEXT,
        simple_value TEXT,
        advanced_value TEXT,
        delta REAL,
        improved INTEGER,
        material_change INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_exit_optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        start_date TEXT,
        end_date TEXT,
        objective TEXT,
        best_params_json TEXT,
        best_total_return REAL,
        best_max_drawdown REAL,
        best_profit_factor REAL,
        best_trades_count INTEGER,
        overfitting_warning INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_exit_optimization_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        params_json TEXT,
        total_return REAL,
        max_drawdown REAL,
        sharpe REAL,
        sortino REAL,
        win_rate REAL,
        profit_factor REAL,
        trades_count INTEGER,
        turnover REAL,
        score_objective REAL,
        overfit_risk_hint TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_walk_forward_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        train_months INTEGER,
        test_months INTEGER,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_test_return REAL,
        mean_test_drawdown REAL,
        mean_test_profit_factor REAL,
        robustness_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_walk_forward_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        train_start TEXT,
        train_end TEXT,
        test_start TEXT,
        test_end TEXT,
        best_params_json TEXT,
        train_return REAL,
        test_return REAL,
        train_drawdown REAL,
        test_drawdown REAL,
        train_profit_factor REAL,
        test_profit_factor REAL,
        train_trades INTEGER,
        test_trades INTEGER,
        test_positive INTEGER,
        overfitting_flag INTEGER,
        turnover_warning INTEGER,
        drawdown_warning INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_scenario_validation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT,
        finished_at TEXT,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        periods_count INTEGER,
        scenarios_count INTEGER,
        signal_sources_count INTEGER,
        positive_periods_pct REAL,
        mean_return REAL,
        mean_drawdown REAL,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_scenario_validation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        period_id INTEGER,
        scenario_id TEXT,
        scenario_name TEXT,
        signal_source TEXT,
        start_date TEXT,
        end_date TEXT,
        total_return REAL,
        max_drawdown REAL,
        sharpe REAL,
        sortino REAL,
        win_rate REAL,
        profit_factor REAL,
        trades_count INTEGER,
        turnover REAL,
        cost_bps REAL,
        slippage_bps REAL,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_cost_sensitivity_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        cost_scenario TEXT,
        cost_bps REAL,
        slippage_bps REAL,
        mean_return REAL,
        mean_drawdown REAL,
        positive_periods_pct REAL,
        cost_robustness_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_signal_source_comparison (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        signal_source TEXT,
        mean_return REAL,
        mean_drawdown REAL,
        win_rate REAL,
        profit_factor REAL,
        trades_count INTEGER,
        robustness_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_fragility_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        source_run_id INTEGER,
        status TEXT,
        total_trades INTEGER,
        total_net_pnl REAL,
        fragility_score REAL,
        fragility_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_fragility_by_asset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        ticker TEXT,
        trades_count INTEGER,
        net_pnl REAL,
        win_rate REAL,
        contribution_pct REAL,
        cost_drag REAL,
        drawdown_contribution REAL,
        fragility_score REAL,
        fragility_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_fragility_by_signal_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        signal_source TEXT,
        trades_count INTEGER,
        net_pnl REAL,
        win_rate REAL,
        contribution_pct REAL,
        cost_drag REAL,
        fragility_score REAL,
        fragility_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_drawdown_periods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        drawdown_start TEXT,
        drawdown_trough TEXT,
        drawdown_recovery TEXT,
        depth REAL,
        duration_days INTEGER,
        recovered INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_investigation_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        base_paper_run_id INTEGER,
        base_fragility_run_id INTEGER,
        hypotheses_count INTEGER,
        improved_count INTEGER,
        rejected_count INTEGER,
        observation_count INTEGER,
        best_hypothesis_id TEXT,
        best_improvement_score REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_investigation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        hypothesis_id TEXT,
        hypothesis_type TEXT,
        target TEXT,
        title TEXT,
        simulated_return REAL,
        simulated_drawdown REAL,
        simulated_trades INTEGER,
        simulated_win_rate REAL,
        simulated_profit_factor REAL,
        fragility_score_before REAL,
        fragility_score_after REAL,
        improvement_score REAL,
        governance_status TEXT,
        conclusion TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_oos_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        hypothesis_id TEXT,
        hypothesis_type TEXT,
        target TEXT,
        windows_count INTEGER,
        scenarios_count INTEGER,
        positive_improvement_pct REAL,
        mean_return_delta REAL,
        mean_drawdown_delta REAL,
        mean_fragility_delta REAL,
        robustness_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_oos_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        scenario_name TEXT,
        signal_source TEXT,
        start_date TEXT,
        end_date TEXT,
        base_return REAL,
        hypothesis_return REAL,
        return_delta REAL,
        base_drawdown REAL,
        hypothesis_drawdown REAL,
        drawdown_delta REAL,
        base_fragility_score REAL,
        hypothesis_fragility_score REAL,
        fragility_delta REAL,
        trades_count INTEGER,
        improvement_detected INTEGER,
        overfitting_flag INTEGER,
        cost_sensitivity_flag INTEGER,
        regime_instability_flag INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_oos_coverage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        scenario_name TEXT,
        signal_source TEXT,
        regime_filter TEXT,
        start_date TEXT,
        end_date TEXT,
        signals_count INTEGER,
        price_days_count INTEGER,
        tickers_count INTEGER,
        useful_cell INTEGER,
        source_coverage_status TEXT,
        message TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_coverage_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        start_date TEXT,
        end_date TEXT,
        sources_checked TEXT,
        coverage_status TEXT,
        useful_cells_pct REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_coverage_by_source (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        signal_source TEXT,
        signals_count INTEGER,
        tickers_count INTEGER,
        active_days_count INTEGER,
        regimes_count INTEGER,
        useful_cells_count INTEGER,
        coverage_pct REAL,
        coverage_status TEXT,
        requirements_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_ranking_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        hypotheses_count INTEGER,
        sources_count INTEGER,
        scenarios_count INTEGER,
        robust_count INTEGER,
        promising_count INTEGER,
        rejected_count INTEGER,
        best_hypothesis_id TEXT,
        best_score REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_ranking_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        hypothesis_id TEXT,
        signal_source TEXT,
        scenario_name TEXT,
        positive_improvement_pct REAL,
        mean_return_delta REAL,
        mean_drawdown_delta REAL,
        mean_fragility_delta REAL,
        cost_sensitivity_flag INTEGER,
        overfitting_flag INTEGER,
        source_diversity_score REAL,
        hypothesis_robustness_score REAL,
        hypothesis_class TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_deep_oos_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        hypotheses_count INTEGER,
        start_date TEXT,
        end_date TEXT,
        status TEXT,
        best_hypothesis_id TEXT,
        approved_count INTEGER,
        blocked_count INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_deep_oos_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        hypothesis_id TEXT,
        signal_source TEXT,
        cost_scenario TEXT,
        slippage_scenario TEXT,
        regime TEXT,
        ticker TEXT,
        windows_count INTEGER,
        trades_count INTEGER,
        mean_return_delta REAL,
        mean_drawdown_delta REAL,
        mean_fragility_delta REAL,
        positive_improvement_pct REAL,
        block_reason TEXT,
        governance_status TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS paper_hypothesis_block_reasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        hypothesis_id TEXT,
        primary_block_reason TEXT,
        secondary_block_reason TEXT,
        explanation TEXT,
        required_actions_json TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_regime_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_date TEXT,
        primary_regime TEXT,
        trend_regime TEXT,
        volatility_regime TEXT,
        liquidity_regime TEXT,
        risk_regime TEXT,
        regime_confidence REAL,
        market_return_mean REAL,
        market_return_median REAL,
        pct_assets_positive REAL,
        total_volume REAL,
        universe_volatility REAL,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS regime_backtest_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        regime_type TEXT,
        regime_value TEXT,
        signals_count INTEGER,
        mean_gross_return_5d REAL,
        mean_net_return_5d REAL,
        hit_rate_5d REAL,
        tradeable_pct REAL,
        top_asset_concentration_pct REAL,
        best_signal_type TEXT,
        best_score_bucket TEXT,
        robustness_class TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quality_filter_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        source_backtest_run_id INTEGER,
        filters_json TEXT,
        signals_before INTEGER,
        signals_after INTEGER,
        removed_pct REAL,
        mean_net_return_before REAL,
        mean_net_return_after REAL,
        hit_rate_before REAL,
        hit_rate_after REAL,
        best_signal_type TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS threshold_optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        source_backtest_run_id INTEGER,
        param_grid_json TEXT,
        best_params_json TEXT,
        best_mean_net_return REAL,
        best_hit_rate REAL,
        best_samples INTEGER,
        overfitting_warning TEXT,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS filter_walk_forward_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        train_months INTEGER,
        test_months INTEGER,
        objective TEXT,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_test_net_return REAL,
        mean_test_hit_rate REAL,
        avg_test_signals REAL,
        avg_top_3_concentration_pct REAL,
        robustness_class TEXT,
        overfitting_alert INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS filter_walk_forward_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        train_start TEXT,
        train_end TEXT,
        test_start TEXT,
        test_end TEXT,
        best_params_json TEXT,
        train_signals INTEGER,
        test_signals INTEGER,
        train_mean_net_return REAL,
        test_mean_net_return REAL,
        train_hit_rate REAL,
        test_hit_rate REAL,
        top_asset_concentration_pct REAL,
        top_3_assets_concentration_pct REAL,
        positive_test_window INTEGER,
        overfitting_flag INTEGER,
        sample_warning INTEGER,
        concentration_warning INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS governance_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        source_type TEXT,
        source_run_id INTEGER,
        candidate_name TEXT,
        governance_status TEXT,
        approved INTEGER,
        risk_level TEXT,
        confidence_level TEXT,
        total_signals INTEGER,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_net_return REAL,
        mean_hit_rate REAL,
        avg_top_3_concentration_pct REAL,
        overfitting_alert INTEGER,
        sample_warning INTEGER,
        concentration_warning INTEGER,
        liquidity_warning INTEGER,
        regime_status TEXT,
        allowed_regimes_json TEXT,
        blocked_regimes_json TEXT,
        event_status TEXT,
        allowed_event_contexts_json TEXT,
        blocked_event_contexts_json TEXT,
        summary_text TEXT,
        reasons_for_json TEXT,
        reasons_against_json TEXT,
        required_actions_json TEXT,
        metadata_json TEXT
    )
    """)
    _ensure_columns(cur, "governance_reviews", GOVERNANCE_REVIEW_EXTRA_COLUMNS)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS walk_forward_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        train_months INTEGER,
        test_months INTEGER,
        horizon INTEGER,
        windows_count INTEGER,
        positive_windows_pct REAL,
        mean_test_return REAL,
        mean_test_hit_rate REAL,
        overfitting_alert INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS walk_forward_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        window_id INTEGER,
        train_start TEXT,
        train_end TEXT,
        test_start TEXT,
        test_end TEXT,
        best_train_signal_type TEXT,
        test_return_best_signal REAL,
        test_hit_rate_best_signal REAL,
        best_train_score_bucket TEXT,
        test_return_best_bucket REAL,
        test_hit_rate_best_bucket REAL,
        degradation_score REAL,
        overfitting_flag INTEGER,
        metadata_json TEXT
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_profit_asset_time ON profit_snapshots(asset, captured_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cotahist_ticker_date ON cotahist_daily(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cotahist_option_exp ON cotahist_daily(option_type, expiration_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_journal_ativo ON trade_journal(ativo, data_sinal)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_greeks_underlying_date ON options_greeks_snapshot(underlying, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_greeks_ticker ON options_greeks_snapshot(ticker, captured_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_options_chain_snapshots_underlying ON options_chain_snapshots(underlying, maturity_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_structure_candidates_underlying ON option_structure_candidates(underlying, maturity_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_scanner_runs_started ON option_scanner_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_structure_backtest_runs_started ON option_structure_backtest_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_structure_backtest_results_run ON option_structure_backtest_results(run_id, underlying)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_walk_forward_runs_started ON option_walk_forward_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_walk_forward_results_run ON option_walk_forward_results(run_id, window_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_option_context_summary_run ON option_context_summary(run_id, context_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_feature_snapshots_ticker ON technical_feature_snapshots(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_setup_signals_ticker ON technical_setup_signals(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_backtest_runs_started ON technical_backtest_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_backtest_results_run ON technical_backtest_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_walk_forward_runs_started ON technical_walk_forward_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_walk_forward_results_run ON technical_walk_forward_results(run_id, window_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_threshold_optimization_runs_created ON technical_threshold_optimization_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_technical_setup_dedup_runs_created ON technical_setup_dedup_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_score_calibration_runs_created ON score_calibration_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_score_calibration_assets_run ON score_calibration_assets(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_score_calibration_assets_asset ON score_calibration_assets(asset, captured_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_historical_backtest_runs_created ON historical_backtest_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_historical_backtest_results_run ON historical_backtest_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_historical_backtest_results_ticker ON historical_backtest_results(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_events_ticker_date ON market_events(ticker, event_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_events_type_date ON market_events(event_type, event_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_coverage_runs_created ON event_coverage_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_coverage_by_regime_run ON event_coverage_by_regime(coverage_run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_event_coverage_by_regime_value ON event_coverage_by_regime(regime_type, regime_value)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_source_health_checks_source ON source_health_checks(source_name, checked_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_routine_runs_started ON daily_routine_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_operational_alerts_open ON operational_alerts(resolved, severity, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_source_sla_snapshots_source ON source_sla_snapshots(source_name, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_operational_observability_created ON operational_observability_snapshots(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_retention_cleanup_runs_started ON retention_cleanup_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_retention_cleanup_details_run ON retention_cleanup_details(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_intelligence_ticker_date ON asset_intelligence_snapshots(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_intelligence_created ON asset_intelligence_snapshots(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_intelligence_diffs_ticker ON asset_intelligence_diffs(ticker, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_intelligence_diffs_material ON asset_intelligence_diffs(material_change, material_change_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_source_audit_runs_started ON data_source_audit_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_source_audit_results_run ON data_source_audit_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_source_audit_results_source ON data_source_audit_results(source_name, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_source_traceability_ticker ON data_source_traceability(ticker, source_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_file_manifest_active ON data_file_manifest(active, source_domain)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_file_manifest_path ON data_file_manifest(file_path)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_file_manifest_runs_started ON data_file_manifest_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_reconciliation_runs_started ON data_reconciliation_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_reconciliation_results_run ON data_reconciliation_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_data_reconciliation_results_source ON data_reconciliation_results(source_domain, issue_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_assistant_runs_started ON ingestion_assistant_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_assistant_steps_run ON ingestion_assistant_steps(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_post_ingestion_validation_run ON post_ingestion_validation_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_comparison_run ON ingestion_reliability_comparison(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_volatility_estimates_ticker ON volatility_estimates(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_snapshots_ticker ON risk_snapshots(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_var_estimates_ticker ON var_estimates(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_position_sizing_ticker ON position_sizing_snapshots(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stress_test_results_ticker ON stress_test_results(ticker, scenario)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_governance_reviews_ticker ON risk_governance_reviews(ticker, created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_runs_started ON paper_simulation_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_orders_run ON paper_orders(run_id, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_positions_run ON paper_positions(run_id, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_equity_run ON paper_equity_curve(run_id, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_exit_events_run ON paper_exit_events(run_id, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_rebalance_events_run ON paper_rebalance_events(run_id, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_pnl_attribution_run ON paper_pnl_attribution(run_id, attribution_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_comparisons_runs ON paper_simulation_comparisons(simple_run_id, advanced_run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_exit_optimization_runs_created ON paper_exit_optimization_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_exit_optimization_results_run ON paper_exit_optimization_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_walk_forward_runs_started ON paper_walk_forward_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_walk_forward_results_run ON paper_walk_forward_results(run_id, window_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_scenario_runs_started ON paper_scenario_validation_runs(started_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_scenario_results_run ON paper_scenario_validation_results(run_id, period_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_cost_sensitivity_run ON paper_cost_sensitivity_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_signal_source_run ON paper_signal_source_comparison(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_fragility_runs_created ON paper_fragility_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_fragility_asset_run ON paper_fragility_by_asset(run_id, ticker)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_fragility_source_run ON paper_fragility_by_signal_source(run_id, signal_source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_drawdown_periods_run ON paper_drawdown_periods(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_investigation_runs_created ON paper_investigation_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_investigation_results_run ON paper_investigation_results(run_id, hypothesis_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_hypothesis_oos_runs_created ON paper_hypothesis_oos_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_hypothesis_oos_results_run ON paper_hypothesis_oos_results(run_id, window_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_paper_hypothesis_oos_coverage_run ON paper_hypothesis_oos_coverage(run_id, window_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_coverage_runs_created ON signal_coverage_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_coverage_by_source_run ON signal_coverage_by_source(run_id, signal_source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_ranking_runs_created ON paper_hypothesis_ranking_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_ranking_results_run ON paper_hypothesis_ranking_results(run_id, hypothesis_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_deep_oos_runs_created ON paper_hypothesis_deep_oos_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_deep_oos_results_run ON paper_hypothesis_deep_oos_results(run_id, hypothesis_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hypothesis_block_reasons_run ON paper_hypothesis_block_reasons(run_id, hypothesis_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_event_links_signal ON signal_event_links(ticker, signal_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_regime_daily_date ON market_regime_daily(trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_regime_backtest_summary_run ON regime_backtest_summary(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quality_filter_runs_created ON quality_filter_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_threshold_optimization_runs_created ON threshold_optimization_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_filter_walk_forward_runs_created ON filter_walk_forward_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_filter_walk_forward_results_run ON filter_walk_forward_results(run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_governance_reviews_created ON governance_reviews(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_governance_reviews_source ON governance_reviews(source_type, source_run_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_walk_forward_runs_created ON walk_forward_runs(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_walk_forward_results_run ON walk_forward_results(run_id)")

    con.commit()
    con.close()

    if verbose:
        print(f"Banco criado/atualizado em: {db_path}")
        print("  - View b3_quotes criada (compatibilidade com scanner legado)")
        print("  - Tabela trade_journal criada")
        print("  - Tabela options_greeks_snapshot criada (IV implícita + Greeks completos)")
        print("  - Tabelas options_chain_snapshots, option_structure_candidates e option_scanner_runs criadas")
        print("  - Tabelas option_structure_backtest_* criadas")
        print("  - Tabelas option_walk_forward_* e option_context_summary criadas")
        print("  - Tabelas technical_feature_snapshots, technical_setup_signals e technical_backtest_* criadas")
        print("  - Tabelas technical_walk_forward_*, technical_threshold_optimization_runs e technical_setup_dedup_runs criadas")
        print("  - Tabelas score_calibration_* criadas")
        print("  - Tabelas historical_backtest_* criadas")
        print("  - Tabelas market_events, signal_event_links e event_context_runs criadas")
        print("  - Tabelas event_coverage_runs e event_coverage_by_regime criadas")
        print("  - Tabelas source_health_checks, daily_routine_runs e operational_alerts criadas")
        print("  - Tabelas source_sla_snapshots e operational_observability_snapshots criadas")
        print("  - Tabelas retention_cleanup_* criadas")
        print("  - Tabela asset_intelligence_snapshots criada")
        print("  - Tabela asset_intelligence_diffs criada")
        print("  - Tabelas data_source_audit_* e data_source_traceability criadas")
        print("  - Tabelas data_file_manifest_* e data_reconciliation_* criadas")
        print("  - Tabelas ingestion_assistant_* e post_ingestion_validation_* criadas")
        print("  - Tabelas volatility_estimates, risk_snapshots, var_estimates, position_sizing_snapshots, stress_test_results e risk_governance_reviews criadas")
        print("  - Tabelas paper_simulation_runs, paper_orders, paper_positions e paper_equity_curve criadas")
        print("  - Tabelas paper_exit_events, paper_rebalance_events e paper_pnl_attribution criadas")
        print("  - Tabelas paper_simulation_comparisons, paper_exit_optimization_* e paper_walk_forward_* criadas")
        print("  - Tabelas paper_scenario_validation_*, paper_cost_sensitivity_results e paper_signal_source_comparison criadas")
        print("  - Tabelas paper_fragility_* e paper_drawdown_periods criadas")
        print("  - Tabelas paper_investigation_* criadas")
        print("  - Tabelas paper_hypothesis_oos_* criadas")
        print("  - Tabelas signal_coverage_runs e signal_coverage_by_source criadas")
        print("  - Tabelas paper_hypothesis_ranking_* criadas")
        print("  - Tabelas paper_hypothesis_deep_oos_* e paper_hypothesis_block_reasons criadas")
        print("  - Tabelas market_regime_daily e regime_backtest_summary criadas")
        print("  - Tabelas quality_filter_runs e threshold_optimization_runs criadas")
        print("  - Tabelas filter_walk_forward_* criadas")
        print("  - Tabela governance_reviews criada")
        print("  - Tabelas walk_forward_* criadas")


def main():
    cfg = load_config()
    init_database(project_path(cfg["database_path"]))


if __name__ == "__main__":
    main()
