import argparse
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.collectors.profit_excel_collector import read_profit_excel, normalize_profit_df, save_snapshots
from src.quant.calibration_store import save_calibration_run
from src.quant.explanations import explain_signal
from src.quant.liquidity import liquidity_profile
from src.quant.score_comparison import compare_scores, score_distribution_report, textual_comparison_report
from src.quant.scoring import score_asset
from src.quant.signals import classify_asset_signal
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

    avg_volume = pd.to_numeric(df.get("volume"), errors="coerce").mean()
    avg_trades = pd.to_numeric(df.get("trades"), errors="coerce").mean()

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

        metrics = {
            "variation_pct": r.get("variation_pct"),
            "last_vs_open_pct": r.get("last_vs_open_pct"),
            "last_vs_prev_close_pct": (
                (r["last"] / r["prev_close"] - 1) * 100
                if pd.notna(r.get("last")) and pd.notna(r.get("prev_close")) and r.get("prev_close") != 0
                else 0
            ),
            "position_range_pct": r.get("position_range_pct"),
            "range_pct": r.get("range_pct"),
            "gap_pct": r.get("gap_pct"),
        }
        liquidity = liquidity_profile(
            volume=r.get("volume"),
            trades=r.get("trades"),
            avg_volume=avg_volume,
            avg_trades=avg_trades,
            min_volume=vol_min,
            min_trades=neg_min,
        )
        trend = {
            "price_above_fast_ma": pd.notna(r.get("last")) and pd.notna(r.get("open")) and r.get("last") > r.get("open"),
            "price_above_slow_ma": pd.notna(r.get("last")) and pd.notna(r.get("prev_close")) and r.get("last") > r.get("prev_close"),
            "fast_ma_above_slow_ma": pd.notna(r.get("open")) and pd.notna(r.get("prev_close")) and r.get("open") >= r.get("prev_close"),
        }
        quant_score = score_asset(metrics=metrics, liquidity=liquidity, trend=trend)
        quant_signal = classify_asset_signal(quant_score)

        item.update({
            "score_final": quant_score["score_final"],
            "score_momentum": quant_score["score_momentum"],
            "score_tendencia": quant_score["score_tendencia"],
            "score_liquidez": quant_score["score_liquidez"],
            "score_volatilidade": quant_score["score_volatilidade"],
            "score_risco": quant_score["score_risco"],
            "signal_type": quant_signal["signal_type"],
            "signal_confidence": quant_signal["confidence"],
            "explanation": explain_signal(
                ticker=str(r.get("asset")),
                signal_type=quant_signal["signal_type"],
                metrics=metrics,
                liquidity=liquidity,
                risks=quant_score["risk_reasons"],
            ),
        })
        rows.append(item)

    out = pd.DataFrame(rows)
    return out.sort_values(["score", "volume", "trades"], ascending=False)

def save_realtime_signals(df, db_path):
    if df is None or df.empty:
        return
    cols = [
        "captured_at", "asset", "last", "variation_pct", "volume", "trades",
        "score", "signal", "motivos",
        "score_final", "score_momentum", "score_tendencia", "score_liquidez",
        "score_volatilidade", "score_risco", "signal_type", "signal_confidence",
        "explanation",
    ]
    save = df[[c for c in cols if c in df.columns]].copy()
    con = sqlite3.connect(db_path)
    save.to_sql("realtime_signals", con, if_exists="append", index=False)
    con.close()

def write_report(df, reports_dir, comparison=False):
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "score_comparison" if comparison else "scanner_realtime"
    path = reports_dir / f"{prefix}_{stamp}.csv"
    cols = [
        "captured_at", "asset", "last", "open", "high", "low", "prev_close",
        "variation_pct", "volume", "trades", "position_range_pct", "score",
        "signal", "motivos", "score_final", "score_momentum", "score_tendencia",
        "score_liquidez", "score_volatilidade", "score_risco", "signal_type",
        "signal_confidence", "divergence_type", "explanation",
    ]
    df[[c for c in cols if c in df.columns]].to_csv(path, index=False, sep=";", decimal=",")
    return path

def run_once(
    cfg,
    save_db=True,
    print_top=10,
    write_csv=False,
    demo=False,
    compare_scores_flag=False,
    save_calibration=False,
):
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

    report_df = ranked
    if compare_scores_flag:
        comparison = compare_scores(ranked)
        dist = score_distribution_report(comparison)
        print("\nCOMPARAÇÃO SCORE LEGADO x SCORE QUANTITATIVO")
        print(textual_comparison_report(comparison, dist))
        detail_cols = ["asset", "score", "score_final", "rank_change", "signal", "signal_type", "divergence_type"]
        print("\n" + comparison[[c for c in detail_cols if c in comparison.columns]].head(print_top).to_string(index=False))
        if save_calibration:
            run_id = save_calibration_run(
                comparison,
                dist,
                dist.get("inflation_alert", {}),
                db_path,
                source="realtime_demo" if demo else "realtime",
            )
            print(f"\nCalibração salva no banco. run_id={run_id}")
        report_df = comparison
    elif save_calibration:
        print("\nAviso: use --compare-scores junto com --save-calibration para salvar a calibração.")

    if write_csv:
        report_path = write_report(report_df, project_path("data/reports"), comparison=compare_scores_flag)
        print(f"Relatório salvo: {report_path}")

    return report_df

def main():
    parser = argparse.ArgumentParser(description="Robô de leitura do Excel RTD do Profit + scanner intraday.")
    parser.add_argument("--once", action="store_true", help="Roda apenas uma leitura e encerra.")
    parser.add_argument("--interval", type=int, default=None, help="Intervalo em segundos entre leituras.")
    parser.add_argument("--top", type=int, default=10, help="Quantidade de ativos para exibir no ranking.")
    parser.add_argument("--csv", action="store_true", help="Salva um CSV do ranking a cada rodada.")
    parser.add_argument("--demo", action="store_true", help="Roda com dados simulados para testar fora do pregão.")
    parser.add_argument("--compare-scores", action="store_true", help="Compara score legado com score quantitativo composto.")
    parser.add_argument("--save-calibration", action="store_true", help="Salva a rodada de comparação de scores no SQLite.")
    args = parser.parse_args()

    cfg = load_config()
    interval = args.interval or int(cfg.get("snapshot_interval_seconds", 5))

    if args.once:
        run_once(
            cfg,
            print_top=args.top,
            write_csv=args.csv,
            demo=args.demo,
            compare_scores_flag=args.compare_scores,
            save_calibration=args.save_calibration,
        )
        return

    print("Robô Profit RTD iniciado. Deixe Profit e Excel abertos. Para parar: CTRL+C.")
    while True:
        try:
            run_once(
                cfg,
                print_top=args.top,
                write_csv=args.csv,
                demo=args.demo,
                compare_scores_flag=args.compare_scores,
                save_calibration=args.save_calibration,
            )
        except KeyboardInterrupt:
            print("\nRobô encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"Erro na leitura/scanner: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    main()
