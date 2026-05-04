"""
CLI — Gerador de Relatórios

Uso:
    python run_report.py
    python run_report.py --capital 50000 --account 50000 --risk 0.01
    python run_report.py --plans   # exibe planos operacionais dos setups aprovados
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import load_quant_config, run_strategy
from src.reports.report_generator import generate_all_reports
from src.quant.execution_assistant import generate_execution_plans


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerador de Relatórios — CALL_CONTINUIDADE")
    parser.add_argument("--capital", type=float, default=10_000)
    parser.add_argument("--account", type=float, default=10_000)
    parser.add_argument("--risk", type=float, default=0.005)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--plans", action="store_true", help="Exibe planos operacionais dos setups aprovados.")
    args = parser.parse_args()

    print("=" * 60)
    print("GERADOR DE RELATÓRIOS — CALL_CONTINUIDADE")
    print("=" * 60)

    cfg = load_config()
    qcfg = load_quant_config()
    db_path = project_path(cfg["database_path"])

    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        return

    con = sqlite3.connect(db_path)
    try:
        df = run_strategy(
            con=con, cfg=cfg, qcfg=qcfg,
            account=args.account, risk=args.risk,
            min_volume=qcfg.get("min_volume_opcao", 100_000),
            min_trades=qcfg.get("min_negocios_opcao", 10),
            min_dte=qcfg.get("min_dte", 15),
            max_dte=qcfg.get("max_dte", 45),
            top=args.top,
        )
    finally:
        con.close()

    generate_all_reports(df, capital=args.capital, verbose=True)

    if args.plans:
        plans = generate_execution_plans(df)
        if plans:
            print(f"\n{len(plans)} planos operacionais gerados:\n")
            for plan in plans:
                print(plan.to_terminal())
        else:
            print("\nNenhum plano operacional gerado (sem setups ENTRADA_VALIDADA ou AGUARDAR_GATILHO).")


if __name__ == "__main__":
    main()
