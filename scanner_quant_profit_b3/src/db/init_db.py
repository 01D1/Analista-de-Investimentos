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
        print("  - Tabelas score_calibration_* criadas")
        print("  - Tabelas historical_backtest_* criadas")
        print("  - Tabelas market_events, signal_event_links e event_context_runs criadas")
        print("  - Tabelas event_coverage_runs e event_coverage_by_regime criadas")
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
