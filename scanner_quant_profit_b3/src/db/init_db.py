import sqlite3
from src.utils import load_config, project_path


def main():
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
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

    # View de compatibilidade para combined_stock_options_scanner.
    # Só é criada se b3_quotes ainda não existir como TABLE (caso já exista
    # como tabela real, é preservada para não perder dados do coletor legado).
    existing = cur.execute(
        "SELECT type FROM sqlite_master WHERE name='b3_quotes'"
    ).fetchone()
    if existing is None:
        cur.execute("""
        CREATE VIEW b3_quotes AS
        SELECT
            trade_date,
            ticker,
            option_type       AS asset_type,
            close,
            strike            AS option_exercise_price,
            expiration_date   AS option_maturity,
            volume,
            trades,
            quantity
        FROM cotahist_daily
        WHERE option_type IN ('CALL', 'PUT')
        """)
    elif existing[0] == 'view':
        cur.execute("DROP VIEW b3_quotes")
        cur.execute("""
        CREATE VIEW b3_quotes AS
        SELECT
            trade_date,
            ticker,
            option_type       AS asset_type,
            close,
            strike            AS option_exercise_price,
            expiration_date   AS option_maturity,
            volume,
            trades,
            quantity
        FROM cotahist_daily
        WHERE option_type IN ('CALL', 'PUT')
        """)

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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_profit_asset_time ON profit_snapshots(asset, captured_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cotahist_ticker_date ON cotahist_daily(ticker, trade_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cotahist_option_exp ON cotahist_daily(option_type, expiration_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_journal_ativo ON trade_journal(ativo, data_sinal)")

    con.commit()
    con.close()
    print(f"Banco criado/atualizado em: {db_path}")
    print("  - View b3_quotes criada (compatibilidade com scanner legado)")
    print("  - Tabela trade_journal criada")


if __name__ == "__main__":
    main()
