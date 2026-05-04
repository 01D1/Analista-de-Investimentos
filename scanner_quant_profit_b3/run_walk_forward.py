"""
CLI — Walk-Forward Analysis

Uso:
    python run_walk_forward.py
    python run_walk_forward.py --capital 50000 --anchored
    python run_walk_forward.py --rolling --train-days 252 --test-days 63
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
from src.quant.walk_forward import WalkForwardEngine, WalkForwardConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-Forward Analysis — CALL_CONTINUIDADE")
    parser.add_argument("--capital", type=float, default=10_000)
    parser.add_argument("--anchored", action="store_true", default=True)
    parser.add_argument("--rolling", action="store_true")
    parser.add_argument("--train-days", type=int, default=252)
    parser.add_argument("--test-days", type=int, default=63)
    parser.add_argument("--min-trades", type=int, default=5)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("WALK-FORWARD ANALYSIS — CALL_CONTINUIDADE")
    print("=" * 60)

    cfg = load_config()
    qcfg = load_quant_config()
    db_path = project_path(cfg["database_path"])

    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        return

    # Gera sinais com o scanner
    con = sqlite3.connect(db_path)
    try:
        df = run_strategy(
            con=con, cfg=cfg, qcfg=qcfg,
            account=args.capital, risk=qcfg.get("risco_por_trade", 0.005),
            min_volume=qcfg.get("min_volume_opcao", 100_000),
            min_trades=qcfg.get("min_negocios_opcao", 10),
            min_dte=qcfg.get("min_dte", 15),
            max_dte=qcfg.get("max_dte", 45),
            top=50,
        )
    finally:
        con.close()

    if df.empty or "final_score" not in df.columns:
        print("Sem setups suficientes para walk-forward.")
        return

    # Usa o score como proxy de P&L (score - threshold) para análise de consistência
    threshold = float(qcfg.get("score_entrada_validada", 70))
    pnl_proxy = df["final_score"] - threshold

    dates = pd.to_datetime(df.get("trade_date", pd.Series([pd.Timestamp.now()] * len(df))))

    wf_cfg = WalkForwardConfig(
        train_pct=0.70,
        rolling_window=args.train_days,
        test_window=args.test_days,
        anchored=not args.rolling,
        min_trades_per_window=args.min_trades,
    )

    engine = WalkForwardEngine(wf_cfg)
    result = engine.run_on_pnl(dates, pnl_proxy, capital=args.capital)
    result.print_summary()

    if args.save and result.windows:
        summary = result.summary_df()
        path = project_path("data/reports") / f"walk_forward_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        print(f"Resultado salvo em: {path}")


if __name__ == "__main__":
    main()
