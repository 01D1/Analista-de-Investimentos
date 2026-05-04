import sqlite3
import pandas as pd
import numpy as np

from src.utils import load_config, project_path


def score_row(row, cfg):
    filtros = cfg.get("filtros", {})
    score = 0
    motivos = []

    if row["last"] and row["open"] and row["last"] > row["open"]:
        score += 15; motivos.append("acima da abertura")
    if row["last"] and row["prev_close"] and row["last"] > row["prev_close"]:
        score += 15; motivos.append("acima do fechamento anterior")
    if row["last"] and row["high"] and row["last"] >= row["high"] * filtros.get("rompimento_tolerancia", 0.995):
        score += 25; motivos.append("próximo da máxima do dia")
    if row["variation_pct"] and row["variation_pct"] >= filtros.get("variacao_minima_pct", 0.3):
        score += 15; motivos.append("variação positiva")
    if row["volume"] and row["volume"] >= filtros.get("volume_minimo", 50_000_000):
        score += 15; motivos.append("volume financeiro relevante")
    if row["trades"] and row["trades"] >= filtros.get("negocios_minimos", 1000):
        score += 15; motivos.append("número de negócios relevante")

    return min(score, 100), "; ".join(motivos)


def main():
    cfg = load_config()
    db_path = project_path(cfg["database_path"])
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT * FROM profit_snapshots
        WHERE id IN (
            SELECT MAX(id) FROM profit_snapshots GROUP BY asset
        )
    """, con)
    con.close()

    if df.empty:
        print("Sem snapshots no banco. Rode primeiro o coletor do Profit.")
        return

    scores = df.apply(lambda r: score_row(r, cfg), axis=1)
    df["score"] = [s[0] for s in scores]
    df["motivos"] = [s[1] for s in scores]
    df = df.sort_values("score", ascending=False)

    cols = ["asset", "last", "variation_pct", "volume", "trades", "score", "motivos", "captured_at"]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
