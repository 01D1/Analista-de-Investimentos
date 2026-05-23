"""
Structure Scanner — Varredura de Estruturas de Opções

Escaneia um ou todos os ativos configurados, monta estruturas aderentes
ao cenário detectado e retorna ranking de oportunidades.

Uso como módulo:
    python -m src.options.structure_scanner --asset PETR4 --top 20
    python -m src.options.structure_scanner --all --top 50
    python -m src.options.structure_scanner --asset VALE3 --verbose
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import load_quant_config
from src.options.options_chain import build_chain
from src.options.strategy_builder import classify_market, build_all_strategies, StrategyOpportunity
from src.options.strategy_ranking import rank_strategies, rank_summary


# ---------------------------------------------------------------------------
# Core: varre um ativo
# ---------------------------------------------------------------------------

def _apply_conservative_filter(
    opportunities: List[StrategyOpportunity],
) -> List[StrategyOpportunity]:
    """Mantém apenas estruturas com risco definido e categoria BAIXO ou MODERADO."""
    return [
        o for o in opportunities
        if o.payoff.risk_level == "DEFINIDO"
        and o.payoff.risk_category in ("BAIXO", "MODERADO")
    ]


def scan_asset(
    underlying: str,
    con: sqlite3.Connection,
    cfg: dict,
    qcfg: dict,
    top: int = 20,
    verbose: bool = False,
    mode: str = "normal",
) -> List[StrategyOpportunity]:
    """
    Varre um único ativo e retorna as melhores oportunidades ranqueadas.
    """
    min_dte = int(qcfg.get("min_dte", 10))
    max_dte = int(qcfg.get("max_dte", 60))
    min_vol = float(qcfg.get("min_volume_opcao", 5_000))
    min_tr = int(qcfg.get("min_negocios_opcao", 2))

    # Cadeia de opções
    chain = build_chain(con, underlying, qcfg, min_dte, max_dte, min_vol, min_tr)
    if len(chain) == 0:
        if verbose:
            print(f"  {underlying}: sem opções líquidas na cadeia.")
        return []

    # Classificação de mercado
    condition = classify_market(con, underlying, qcfg)

    if verbose:
        print(f"  {underlying}: {len(chain.calls)}C / {len(chain.puts)}P  "
              f"| HV={chain.hv:.1%} | Cenário={condition.value}")

    # Montar estruturas
    opportunities = build_all_strategies(chain, condition, qcfg)

    if not opportunities:
        if verbose:
            print(f"  {underlying}: nenhuma estrutura montada.")
        return []

    if mode == "conservative":
        opportunities = _apply_conservative_filter(opportunities)
        if not opportunities:
            if verbose:
                print(f"  {underlying}: nenhuma estrutura passou pelo filtro conservador.")
            return []

    # Ranking
    ranked = rank_strategies(opportunities, top=top)
    return ranked


# ---------------------------------------------------------------------------
# Core: varre todos os ativos
# ---------------------------------------------------------------------------

def scan_all(
    con: sqlite3.Connection,
    cfg: dict,
    qcfg: dict,
    top_per_asset: int = 5,
    top_total: int = 50,
    verbose: bool = False,
    mode: str = "normal",
) -> List[StrategyOpportunity]:
    """
    Varre todos os ativos configurados e retorna ranking global.
    """
    ativos = qcfg.get("ativos_permitidos", [])
    all_opps: List[StrategyOpportunity] = []

    for ativo in ativos:
        opps = scan_asset(ativo, con, cfg, qcfg,
                          top=top_per_asset, verbose=verbose, mode=mode)
        all_opps.extend(opps)

    # Reranqueia globalmente
    ranked = rank_strategies(all_opps, top=top_total)
    return ranked


def scan_to_df(opportunities: List[StrategyOpportunity]) -> pd.DataFrame:
    """Converte lista de oportunidades para DataFrame."""
    if not opportunities:
        return pd.DataFrame()

    import math as _math
    rows = []
    for opp in opportunities:
        p = opp.payoff
        be_str = " / ".join(f"{b:.2f}" for b in p.breakevens[:2])
        legs_str = " | ".join(str(l) for l in p.legs)
        rows.append({
            "rank": opp.rank,
            "status": opp.status,
            "score": opp.score,
            "underlying": p.underlying,
            "strategy": p.name,
            "strategy_type": p.strategy_type,
            "risk_category": p.risk_category,
            "suitability": p.suitability,
            "cenario": opp.market_condition.value,
            "adherence": round(opp.scenario_adherence, 2),
            "net_cost": round(p.net_cost, 2),
            "max_profit": round(p.max_profit, 2) if not _math.isinf(p.max_profit) else None,
            "max_loss": round(p.max_loss, 2) if not _math.isinf(p.max_loss) else None,
            "risk_reward": p.risk_reward,
            "breakevens": be_str,
            "prob_profit": round(opp.prob_profit, 4),
            "dte": p.dte,
            "expiry": p.expiry,
            "risk_level": p.risk_level,
            "requires_margin": p.requires_margin,
            "legs": legs_str,
            "stock_price": p.stock_price,
            "hv": round(opp.hv, 4),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Structure Scanner — Varredura de Estruturas de Opções B3"
    )
    parser.add_argument("--asset", type=str, default=None,
                        help="Ativo específico (ex: PETR4). Omitir = todos.")
    parser.add_argument("--all", action="store_true",
                        help="Varre todos os ativos configurados.")
    parser.add_argument("--top", type=int, default=20,
                        help="Número de estruturas a exibir.")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--mode", choices=["normal", "conservative"], default="normal",
                        help="conservative: apenas risco definido + categoria BAIXO/MODERADO.")
    parser.add_argument("--save", action="store_true",
                        help="Salva resultado em CSV.")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    cfg = load_config()
    qcfg = load_quant_config()
    db_path = project_path(cfg["database_path"])

    if not db_path.exists():
        print(f"Banco não encontrado: {db_path}")
        return

    con = sqlite3.connect(db_path)
    try:
        mode_label = f" [{args.mode.upper()}]" if args.mode != "normal" else ""
        if args.asset:
            _print_header(f"STRUCTURE SCANNER — {args.asset.upper()}{mode_label}")
            opps = scan_asset(args.asset.upper(), con, cfg, qcfg,
                              top=args.top, verbose=args.verbose, mode=args.mode)
        else:
            _print_header(f"STRUCTURE SCANNER — TODOS OS ATIVOS{mode_label}")
            opps = scan_all(con, cfg, qcfg, top_per_asset=5,
                           top_total=args.top, verbose=True, mode=args.mode)
    finally:
        con.close()

    if not opps:
        print("\nNenhuma estrutura encontrada com os critérios atuais.")
        print("Dica: verifique se há PUTs no banco ou reduza os filtros de liquidez.")
        return

    print(f"\n{len(opps)} estruturas encontradas:\n")
    print(rank_summary(opps))

    if args.save:
        import pandas as pd
        from datetime import datetime
        df = scan_to_df(opps)
        asset_slug = args.asset.upper() if args.asset else "ALL"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = project_path("data/reports") / f"structures_{asset_slug}_{ts}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        print(f"\nSalvo em: {path}")

    print("\n⚠️  Sistema de apoio à decisão — não executa ordens reais.")


if __name__ == "__main__":
    main()
