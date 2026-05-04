import sqlite3
from src.utils import load_config, project_path

def init_db():
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS profit_snapshots (
        captured_at TEXT,
        asset TEXT,
        last REAL,
        open REAL,
        high REAL,
        low REAL,
        prev_close REAL,
        variation_pct REAL,
        variation_pts REAL,
        trades REAL,
        quantity REAL,
        volume REAL
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS realtime_signals (
        captured_at TEXT,
        asset TEXT,
        last REAL,
        variation_pct REAL,
        volume REAL,
        trades REAL,
        score REAL,
        signal TEXT,
        motivos TEXT
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS b3_quotes (
        trade_date TEXT,
        ticker TEXT,
        market_type INTEGER,
        company_name TEXT,
        open REAL,
        high REAL,
        low REAL,
        average REAL,
        close REAL,
        best_bid REAL,
        best_ask REAL,
        trades INTEGER,
        quantity INTEGER,
        volume REAL,
        option_exercise_price REAL,
        option_maturity TEXT,
        asset_type TEXT
    )
    ''')

    con.commit()
    con.close()
    print(f"Banco inicializado em: {db_path}")

if __name__ == "__main__":
    init_db()
