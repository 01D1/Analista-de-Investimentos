"""Relatório Markdown de paper trading."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _num(value, decimals=2):
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return "-" if pd.isna(parsed) else f"{float(parsed):.{decimals}f}"


def generate_paper_trading_report(
    run_summary: dict,
    orders_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    equity_curve_df: pd.DataFrame,
    exit_events_df: pd.DataFrame | None = None,
    rebalance_events_df: pd.DataFrame | None = None,
    pnl_attribution_df: pd.DataFrame | None = None,
) -> str:
    exit_events_df = exit_events_df if exit_events_df is not None else pd.DataFrame()
    rebalance_events_df = rebalance_events_df if rebalance_events_df is not None else pd.DataFrame()
    pnl_attribution_df = pnl_attribution_df if pnl_attribution_df is not None else pd.DataFrame()
    return f"""# Relatório de Paper Trading

## Resumo
- Status: {run_summary.get('status', '-')}
- Governança: {run_summary.get('governance_status', '-')}
- Capital inicial: {_num(run_summary.get('capital_initial'))}
- Capital final: {_num(run_summary.get('capital_final'))}

## Performance
- Retorno total: {_num(run_summary.get('total_return'), 4)}
- Sharpe: {_num(run_summary.get('sharpe'))}
- Sortino: {_num(run_summary.get('sortino'))}
- Max drawdown: {_num(run_summary.get('max_drawdown'), 4)}
- Win rate: {_num(run_summary.get('win_rate'), 4)}
- Profit factor: {_num(run_summary.get('profit_factor'))}

## Risco
- VaR médio: {_num(run_summary.get('var_avg'))}
- ES médio: {_num(run_summary.get('es_avg'))}
- Exposição média: {_num(run_summary.get('exposure_avg'))}
- Exposição máxima: {_num(run_summary.get('exposure_max'))}

## Ordens Simuladas
Total de ordens simuladas: {len(orders_df) if orders_df is not None else 0}

## Regras de Saída
- Eventos de saída simulada: {len(exit_events_df)}
- Stops/take-profits/trailing/time exits são regras simuladas e auditáveis.

## Rebalanceamento
- Eventos de rebalanceamento simulado: {len(rebalance_events_df)}
- Rebalanceamento por risco/regime é simulado e não altera posições reais.

## P&L Attribution
- Linhas de decomposição de P&L: {len(pnl_attribution_df)}
- A decomposição pode agrupar por fonte de sinal, regime, risco e contexto.

## Posições
Total de registros de posições simuladas: {len(positions_df) if positions_df is not None else 0}

## Drawdown
A curva de equity contém {len(equity_curve_df) if equity_curve_df is not None else 0} pontos.

## Governança
O paper trading é observacional e depende da qualidade dos sinais, risco, liquidez e custos simulados.

## Limitações
Execução, liquidez e slippage são aproximações. Não há envio de ordens reais.

## Não recomendação
Este relatório é apenas simulação analítica e não constitui recomendação financeira.
"""


def save_paper_trading_report(
    run_summary: dict,
    orders_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    equity_curve_df: pd.DataFrame,
    output_dir: str | Path,
    exit_events_df: pd.DataFrame | None = None,
    rebalance_events_df: pd.DataFrame | None = None,
    pnl_attribution_df: pd.DataFrame | None = None,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "paper_trading_report.md"
    path.write_text(generate_paper_trading_report(run_summary, orders_df, positions_df, equity_curve_df, exit_events_df, rebalance_events_df, pnl_attribution_df), encoding="utf-8")
    return path
