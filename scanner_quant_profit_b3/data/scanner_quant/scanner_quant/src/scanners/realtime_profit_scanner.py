import argparse
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.collectors.profit_excel_collector import read_profit_excel, normalize_profit_df, save_snapshots
from src.utils import load_config, project_path

def demo_data():
    rows = [
        {"asset": "PETR4", "last": 39.85, "open": 39.10, "high": 39.90, "low": 38.80, "prev_close": 38.95, "variation_pct": 2.31, "trades": 45500, "quantity": 12000000, "volume": 475000000},
        {"asset": "VALE3", "last": 63.20, "open": 62.90, "high": 63.40, "low": 62.10, "prev_close": 62.50, "variation_pct": 1.12, "trades": 38500, "quantity": 9000000, "volume": 568000000},
        {"asset": "ITUB4", "last": 35.40, "open": 35.80, "high": 35.90, "low": 35.20, "prev_close": 35.70, "variation_pct": -0.84, "trades": 22000, "quantity": 7000000, "volume": 247000000},
        {"asset": "BBAS3", "last": 28.70, "open": 28.20, "high": 28.72, "low": 28.05, "prev_close": 28.10, "variation_pct": 2.14, "trades": 17500, "quantity": 5000000, "volume": 143500000},
    ]
    df = pd.DataFrame(rows)
    df["captured_at"] = datetime.now().isoformat(timespec="seconds")
    return df

def calculate_intraday_metrics(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    for c in ["last", "open", "high", "low", "prev_close", "variation_pct", "trades", "volume"]:
        if c not in df.columns:
            df[c] = None
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["range_pct"] = ((df["high"] - df["low"]) / df["prev_close"] * 100).round(2)
    df["position_range_pct"] = ((df["last"] - df["low"]) / (df["high"] - df["low"]) * 100).replace([float("inf"), -float("inf")], None).round(1)
    df["gap_pct"] = ((df["open"] - df["prev_close"]) / df["prev_close"] * 100).round(2)
    df["last_vs_open_pct"] = ((df["last"] - df["open"]) / df["open"] * 100).round(2)
    return df

def score_realtime(df, cfg):
    if df is None or df.empty:
        return pd.DataFrame()
    filtros = cfg.get("filtros", {})
    romp_tol = float(filtros.get("rompimento_tolerancia", 0.995))
    vol_min = float(filtros.get("volume_minimo", 50000000))
    neg_min = int(filtros.get("negocios_minimos", 1000))
    var_min = float(filtros.get("variacao_minima_pct", 0.3))

    rows = []
    for _, r in df.iterrows():
        score = 0
        motivos = []

        if pd.notna(r["last"]) and pd.notna(r["open"]) and r["last"] > r["open"]:
            score += 12; motivos.append("último acima da abertura")
        if pd.notna(r["last"]) and pd.notna(r["prev_close"]) and r["last"] > r["prev_close"]:
            score += 12; motivos.append("positivo contra fechamento anterior")
        if pd.notna(r["last"]) and pd.notna(r["high"]) and r["last"] >= r["high"] * romp_tol:
            score += 22; motivos.append("próximo da máxima")
        if pd.notna(r["variation_pct"]) and r["variation_pct"] >= var_min:
            score += 12; motivos.append("variação positiva relevante")
        if pd.notna(r["volume"]) and r["volume"] >= vol_min:
            score += 17; motivos.append("volume financeiro relevante")
        if pd.notna(r["trades"]) and r["trades"] >= neg_min:
            score += 12; motivos.append("negócios relevantes")
        if pd.notna(r.get("position_range_pct")) and r["position_range_pct"] >= 75:
            score += 13; motivos.append("fechando no topo do range")

        signal = "NEUTRO"
        if score >= 75:
            signal = "COMPRA/FORÇA"
        elif score >= 55:
            signal = "OBSERVAR"
        elif pd.notna(r.get("position_range_pct")) and r["position_range_pct"] <= 25 and pd.notna(r["variation_pct"]) and r["variation_pct"] < 0:
            signal = "FRAQUEZA"

        item = r.to_dict()
        item["score"] = min(score, 100)
        item["signal"] = signal
        item["motivos"] = "; ".join(motivos)
        rows.append(item)

    out = pd.DataFrame(rows)
    return out.sort_values(["score", "volume", "trades"], ascending=False)

def save_realtime_signals(df, db_path):
    if df is None or df.empty:
        return
    cols = ["captured_at", "asset", "last", "variation_pct", "volume", "trades", "score", "signal", "motivos"]
    save = df[[c for c in cols if c in df.columns]].copy()
    con = sqlite3.connect(db_path)
    save.to_sql("realtime_signals", con, if_exists="append", index=False)
    con.close()

def write_report(df, reports_dir):
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"scanner_realtime_{stamp}.csv"
    cols = ["captured_at", "asset", "last", "open", "high", "low", "prev_close", "variation_pct", "volume", "trades", "position_range_pct", "score", "signal", "motivos"]
    df[[c for c in cols if c in df.columns]].to_csv(path, index=False, sep=";", decimal=",")
    return path

def run_once(cfg, save_db=True, print_top=10, write_csv=False, demo=False):
    db_path = project_path(cfg["database_path"])

    if demo:
        norm = demo_data()
    else:
        path = project_path(cfg["profit_excel_path"])
        sheet = cfg.get("profit_sheet_name", "Planilha1")
        raw = read_profit_excel(path, sheet)
        norm = normalize_profit_df(raw)

    if norm is None or norm.empty or norm["last"].isna().all():
        print("\nSem dados válidos do Profit no momento. Use --demo para testar fora do pregão.")
        return pd.DataFrame()

    metrics = calculate_intraday_metrics(norm)
    ranked = score_realtime(metrics, cfg)

    if save_db:
        save_snapshots(norm, str(db_path))
        save_realtime_signals(ranked, db_path)

    cols = ["asset", "last", "variation_pct", "volume", "trades", "position_range_pct", "score", "signal", "motivos"]
    print("\n" + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print(ranked[cols].head(print_top).to_string(index=False))

    if write_csv:
        report_path = write_report(ranked, project_path("data/reports"))
        print(f"Relatório salvo: {report_path}")

    return ranked

def main():
    parser = argparse.ArgumentParser(description="Robô de leitura do Excel RTD do Profit + scanner intraday.")
    parser.add_argument("--once", action="store_true", help="Roda apenas uma leitura e encerra.")
    parser.add_argument("--interval", type=int, default=None, help="Intervalo em segundos entre leituras.")
    parser.add_argument("--top", type=int, default=10, help="Quantidade de ativos para exibir no ranking.")
    parser.add_argument("--csv", action="store_true", help="Salva um CSV do ranking a cada rodada.")
    parser.add_argument("--demo", action="store_true", help="Roda com dados simulados para testar fora do pregão.")
    args = parser.parse_args()

    cfg = load_config()
    interval = args.interval or int(cfg.get("snapshot_interval_seconds", 5))

    if args.once:
        run_once(cfg, print_top=args.top, write_csv=args.csv, demo=args.demo)
        return

    print("Robô Profit RTD iniciado. Deixe Profit e Excel abertos. Para parar: CTRL+C.")
    while True:
        try:
            run_once(cfg, print_top=args.top, write_csv=args.csv, demo=args.demo)
        except KeyboardInterrupt:
            print("\nRobô encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"Erro na leitura/scanner: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    main()
