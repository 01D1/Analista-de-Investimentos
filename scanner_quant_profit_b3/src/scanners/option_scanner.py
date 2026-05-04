import sqlite3
import pandas as pd
from datetime import date

from src.utils import load_config, project_path


def main():
    cfg = load_config()
    ativos = cfg.get("ativos_base", [])
    db_path = project_path(cfg["database_path"])
    con = sqlite3.connect(db_path)

    placeholders = ",".join(["?"] * len(ativos))
    query = f"""
    WITH last_dates AS (
        SELECT MAX(trade_date) AS dt FROM cotahist_daily
    )
    SELECT * FROM cotahist_daily
    WHERE trade_date = (SELECT dt FROM last_dates)
      AND option_type IN ('CALL','PUT')
    """
    df = pd.read_sql_query(query, con)
    con.close()

    if df.empty:
        print("Sem opções no banco. Importe o COTAHIST primeiro.")
        return

    # Aproxima o ativo objeto pelos 4 primeiros caracteres. Ex.: PETR, VALE, ITUB.
    bases = {a[:4]: a for a in ativos}
    df["base_prefix"] = df["ticker"].str[:4]
    df["ativo_base_estimado"] = df["base_prefix"].map(bases)
    df = df[df["ativo_base_estimado"].notna()].copy()

    today = pd.to_datetime(df["trade_date"]).dt.date
    exp = pd.to_datetime(df["expiration_date"], errors="coerce").dt.date
    df["days_to_expiration"] = [(e - t).days if pd.notna(e) else None for e, t in zip(exp, today)]

    df["score"] = 0
    df.loc[df["trades"] >= 100, "score"] += 30
    df.loc[df["volume"] >= 100000, "score"] += 30
    df.loc[df["days_to_expiration"].between(7, 45, inclusive="both"), "score"] += 25
    df.loc[df["close"] > 0, "score"] += 15

    cols = ["trade_date", "ticker", "ativo_base_estimado", "option_type", "expiration_date", "days_to_expiration", "close", "strike", "trades", "volume", "score"]
    out = df.sort_values(["score", "volume", "trades"], ascending=False)[cols].head(50)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
