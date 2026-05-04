"""
CLI — Backtesting Engine

Executa o backtest histórico da estratégia CALL_CONTINUIDADE.

Modos disponíveis:
  --mode journal   : usa o trade_journal.csv (trades já executados)
  --mode simulate  : simula sobre dados históricos do COTAHIST

Uso:
    python run_backtest.py
    python run_backtest.py --mode journal --capital 50000
    python run_backtest.py --mode simulate --capital 50000 --risk 0.01 --top 20
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import load_quant_config, run_strategy
from src.quant.backtester import BacktestEngine, BacktestConfig
from src.quant.performance import full_summary, drawdown


def mode_journal(args) -> None:
    """Backtest sobre o trade_journal.csv."""
    journal_path = project_path("data/journal/trade_journal.csv")
    if not journal_path.exists():
        print(f"Diário não encontrado: {journal_path}")
        print("Execute a estratégia com --journal primeiro.")
        return

    journal = pd.read_csv(journal_path, sep=";", encoding="utf-8-sig")
    qcfg = load_quant_config()

    engine = BacktestEngine.from_qcfg(qcfg)
    engine.load_from_journal(journal)
    engine.print_summary()

    df = engine.trades_df()
    if not df.empty and args.save:
        path = project_path("data/reports") / f"backtest_journal_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        print(f"Resultado salvo em: {path}")


def mode_simulate(args) -> None:
    """Simula backtest sobre sinais do scanner e preços históricos."""
    cfg = load_config()
    qcfg = load_quant_config()
    db_path = project_path(cfg["database_path"])

    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        return

    con = sqlite3.connect(db_path)
    print("Executando scanner para gerar sinais históricos...")
    try:
        df_setups = run_strategy(
            con=con, cfg=cfg, qcfg=qcfg,
            account=args.capital, risk=args.risk,
            min_volume=qcfg.get("min_volume_opcao", 100_000),
            min_trades=qcfg.get("min_negocios_opcao", 10),
            min_dte=qcfg.get("min_dte", 15),
            max_dte=qcfg.get("max_dte", 45),
            top=args.top,
        )
    finally:
        con.close()

    if df_setups.empty:
        print("Nenhum setup gerado — verifique os dados do banco.")
        return

    # Monta sinais no formato esperado pelo backtester
    signals_df = pd.DataFrame({
        "date": df_setups.get("trade_date", ""),
        "ticker": df_setups.get("ticker", ""),
        "underlying": df_setups.get("underlying", ""),
        "option_type": df_setups.get("option_type", "CALL"),
        "entry_price": df_setups.get("preco_opcao", 0),
        "score": df_setups.get("final_score", 0),
        "dte": df_setups.get("dte", 30),
    })

    # Carrega preços históricos por ativo
    con = sqlite3.connect(db_path)
    price_data = {}
    for ativo in df_setups["underlying"].unique():
        q = """
        SELECT trade_date, AVG(close) as close, MAX(high) as high, MIN(low) as low
        FROM b3_quotes
        WHERE ticker = ? AND asset_type = 'ACAO'
        GROUP BY trade_date ORDER BY trade_date
        """
        try:
            price_data[ativo] = pd.read_sql_query(q, con, params=(ativo,))
        except Exception:
            pass
    con.close()

    engine = BacktestEngine.from_qcfg(qcfg)
    engine.run_from_signals(signals_df, price_data)
    engine.print_summary()

    df = engine.trades_df()
    if not df.empty and args.save:
        path = project_path("data/reports") / f"backtest_simulate_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        print(f"Resultado salvo em: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtesting Engine — CALL_CONTINUIDADE")
    parser.add_argument("--mode", choices=["journal", "simulate"], default="simulate",
                        help="Fonte dos trades: journal (CSV existente) ou simulate (scanner).")
    parser.add_argument("--capital", type=float, default=10_000, help="Capital inicial (R$).")
    parser.add_argument("--risk", type=float, default=0.005, help="Risco por trade (0-1).")
    parser.add_argument("--top", type=int, default=20, help="Nº de setups simulados.")
    parser.add_argument("--save", action="store_true", help="Salva o resultado em CSV.")
    args = parser.parse_args()

    print("=" * 60)
    print("BACKTESTING ENGINE — CALL_CONTINUIDADE")
    print("⚠️  Resultado histórico não garante performance futura.")
    print("=" * 60)

    if args.mode == "journal":
        mode_journal(args)
    else:
        mode_simulate(args)


if __name__ == "__main__":
    main()
