"""
Strategy Report — Relatório Operacional de Estruturas

Gera relatórios formatados em linguagem operacional para decisão manual.

Uso como módulo:
    python -m src.options.strategy_report --asset PETR4
    python -m src.options.strategy_report --all --save
"""
from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import load_config, project_path
from src.strategies.call_continuity_strategy import load_quant_config
from src.options.strategy_builder import StrategyOpportunity
from src.options.structure_scanner import scan_asset, scan_all


# ---------------------------------------------------------------------------
# Formatação de uma estrutura
# ---------------------------------------------------------------------------

def _fmt(value: float, prefix: str = "R$", decimals: int = 2) -> str:
    if math.isinf(value):
        return "ilimitado"
    return f"{prefix}{value:,.{decimals}f}"


def format_strategy_report(opp: StrategyOpportunity, rank: int = None) -> str:
    """Formata o relatório completo de uma oportunidade em texto operacional."""
    p = opp.payoff
    sep = "─" * 68

    header_rank = f"#{rank} " if rank else ""
    risk_tag = "RISCO ILIMITADO" if p.risk_level == "ILIMITADO" else "RISCO DEFINIDO"
    margin_tag = "  | Exige margem" if p.requires_margin else ""

    status = opp.status
    status_icons = {"OPERACIONAL": "✅", "ESTUDO": "📋", "DESCARTAR": "❌"}
    status_icon = status_icons.get(status, "")

    lines = [
        sep,
        f"  {header_rank}{p.name.upper()}  |  {p.underlying}  |  Score: {opp.score:.1f}/100",
        f"  {status_icon} [{status}]  |  {risk_tag}{margin_tag}  |  Risco: {p.risk_category}",
        f"  {opp.why_ranked}",
        sep,
    ]

    # Cenário
    lines += [
        f"  CENÁRIO:    {opp.market_condition.value}  "
        f"(aderência {opp.scenario_adherence:.0%})",
        f"  VISÃO:      {p.market_view}",
        "",
    ]

    # Pernas
    lines.append("  PERNAS DA OPERAÇÃO:")
    for leg in p.legs:
        if leg.option_type == "STOCK":
            lines.append(f"    {'COMPRAR' if leg.direction == 'BUY' else 'VENDER':8}  "
                         f"100 ações de {opp.underlying} @ R${leg.price:.2f}")
        else:
            dir_label = "COMPRAR" if leg.direction == "BUY" else "VENDER "
            margin_note = " [marg]" if leg.direction == "SELL" else ""
            lines.append(
                f"    {dir_label}  {leg.quantity}x {leg.ticker:12}  "
                f"{leg.option_type}  K={leg.strike:.2f}  "
                f"vto={leg.expiry}  ({leg.dte}d)  "
                f"@ R${leg.price:.4f}{margin_note}"
            )

    lines.append("")

    # Financeiro
    cost_label = "DÉBITO    " if p.net_cost > 0 else "CRÉDITO   "
    lines += [
        "  FINANCEIRO (por lote de 100 ações):",
        f"    {cost_label}R${abs(p.net_cost):,.2f}",
        f"    Ganho Máx   {_fmt(p.max_profit)}  "
        f"({'por lote' if not math.isinf(p.max_profit) else ''})",
        f"    Perda Máx   {_fmt(p.max_loss)}",
        (f"    Risco/Retorno  {p.risk_reward:.2f}x" if not math.isinf(p.risk_reward) else
         f"    Risco/Retorno  ilimitado (upside)"),
        "",
    ]

    # Breakevens
    if p.breakevens:
        be_vals = "  /  ".join(f"R${b:.2f}" for b in p.breakevens)
        lines.append(f"  BREAKEVEN(S):  {be_vals}")
        lines.append(f"  Preço atual:   R${p.stock_price:.2f}")

        pct_bes = []
        for be in p.breakevens:
            pct = (be / p.stock_price - 1) * 100
            pct_bes.append(f"{pct:+.1f}%")
        lines.append(f"  Distância:     {' / '.join(pct_bes)} do spot")
        lines.append("")

    # Probabilidade
    lines += [
        f"  PROBABILIDADE DE LUCRO:  {opp.prob_profit:.1%}  "
        f"(modelo lognormal, HV={opp.hv:.1%})",
        f"  DTE: {p.dte} dias  |  Vencimento: {p.expiry}",
        "",
    ]

    # Operacional
    lines += [
        "  ENTRADA:      " + p.entry_condition,
        "  SAÍDA:        " + p.exit_condition,
        "",
        "  QUANDO GANHA: " + p.best_scenario,
        "  QUANDO PERDE: " + p.worst_scenario,
        "",
        "  ⚠️  OBSERVAÇÃO DE RISCO:",
        "  " + p.risk_observation,
        sep,
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Relatório de múltiplas oportunidades
# ---------------------------------------------------------------------------

def generate_asset_report(
    opportunities: List[StrategyOpportunity],
    asset: str,
    save: bool = False,
    verbose: bool = True,
) -> str:
    """Gera relatório completo para um ativo."""
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    header = (
        f"\n{'=' * 68}\n"
        f"  RELATÓRIO DE ESTRUTURAS — {asset.upper()}\n"
        f"  Gerado em: {ts}\n"
        f"{'=' * 68}\n"
    )

    if not opportunities:
        body = "  Nenhuma estrutura encontrada.\n"
    else:
        parts = [
            f"\n  {len(opportunities)} estruturas analisadas:\n",
            format_strategy_report(opportunities[0], rank=1),
        ]
        for i, opp in enumerate(opportunities[1:], start=2):
            parts.append(format_strategy_report(opp, rank=i))
        body = "\n".join(parts)

    footer = (
        "\n" + "=" * 68 + "\n"
        "  ⚠️  Este relatório é exclusivamente educacional.\n"
        "  Não executa ordens reais. Decisão sempre do operador.\n"
        + "=" * 68 + "\n"
    )

    report = header + body + footer

    if verbose:
        print(report)

    if save:
        ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = project_path("data/reports") / f"strategy_report_{asset}_{ts_file}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report, encoding="utf-8")
        print(f"\nRelatório salvo em: {path}")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strategy Report — Relatório de Estruturas de Opções"
    )
    parser.add_argument("--asset", type=str, default=None,
                        help="Ativo específico (ex: VALE3).")
    parser.add_argument("--all", action="store_true",
                        help="Gera relatório para todos os ativos.")
    parser.add_argument("--top", type=int, default=10,
                        help="Número de estruturas por relatório.")
    parser.add_argument("--save", action="store_true",
                        help="Salva relatório em arquivo .txt.")
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
        if args.asset:
            assets = [args.asset.upper()]
        else:
            assets = qcfg.get("ativos_permitidos", [])

        for ativo in assets:
            opps = scan_asset(ativo, con, cfg, qcfg, top=args.top)
            generate_asset_report(opps, ativo, save=args.save, verbose=True)
    finally:
        con.close()


if __name__ == "__main__":
    main()
