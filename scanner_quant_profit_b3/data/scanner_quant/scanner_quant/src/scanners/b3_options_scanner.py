import argparse
import sqlite3
import pandas as pd
from src.utils import load_config, project_path

def scan_options(min_volume=100000, min_trades=10, top=30):
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    con = sqlite3.connect(db_path)

    q = """
    SELECT *
    FROM b3_quotes
    WHERE asset_type IN ('CALL', 'PUT')
      AND volume >= ?
      AND trades >= ?
    """
    df = pd.read_sql(q, con, params=[min_volume, min_trades])
    con.close()

    if df.empty:
        print("Nenhuma opção encontrada com os filtros atuais.")
        return df

    df["liquidity_score"] = 0
    df.loc[df["volume"] >= min_volume, "liquidity_score"] += 40
    df.loc[df["trades"] >= min_trades, "liquidity_score"] += 30
    df.loc[df["quantity"] > 0, "liquidity_score"] += 15
    df.loc[df["close"] > 0, "liquidity_score"] += 15

    out = df.sort_values(["trade_date", "liquidity_score", "volume", "trades"], ascending=[False, False, False, False])
    cols = ["trade_date", "ticker", "asset_type", "close", "option_exercise_price", "option_maturity", "volume", "trades", "quantity", "liquidity_score"]
    print(out[cols].head(top).to_string(index=False))
    return out

def main():
    parser = argparse.ArgumentParser(description="Scanner inicial de opções B3.")
    parser.add_argument("--min-volume", type=float, default=100000)
    parser.add_argument("--min-trades", type=int, default=10)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()
    scan_options(args.min_volume, args.min_trades, args.top)

if __name__ == "__main__":
    main()
