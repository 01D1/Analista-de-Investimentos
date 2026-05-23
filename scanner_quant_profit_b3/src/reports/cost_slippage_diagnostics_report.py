"""Relatório Markdown de diagnóstico de custo e slippage."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidência insuficiente."
    return df[[c for c in cols if c in df.columns]].head(20).to_markdown(index=False)


def generate_cost_slippage_diagnostics_markdown(cost_result: dict, turnover_result: dict | None = None, liquidity_result: dict | None = None, breakeven: dict | None = None) -> str:
    turnover_result = turnover_result or {}
    liquidity_result = liquidity_result or {}
    breakeven = breakeven or {}
    summary = cost_result.get("summary", {}) if cost_result else {}
    turnover = turnover_result.get("summary", {})
    liquidity = liquidity_result.get("summary", {})
    lines = [
        "# Diagnóstico de Custo e Slippage",
        "",
        "## Resumo",
        f"Classe de cost drag: {summary.get('cost_drag_class', 'INSUFFICIENT_DATA')}.",
        f"Classe de liquidez: {liquidity.get('liquidity_class', 'DATA_INSUFFICIENT')}.",
        "",
        "## Custo total",
        f"Transaction cost: {summary.get('total_transaction_cost', 0)}.",
        f"Cost drag total: {summary.get('total_cost_drag', 0)}.",
        f"Cost drag / gross P&L: {summary.get('cost_drag_pct_of_gross_pnl', 0)}.",
        "",
        "## Slippage total",
        f"Slippage cost: {summary.get('total_slippage_cost', 0)}.",
        f"Slippage / gross P&L: {summary.get('slippage_pct_of_gross_pnl', 0)}.",
        "",
        "## Turnover",
        f"Trades por dia: {turnover.get('trades_per_day', 0)}.",
        f"Turnover total: {turnover.get('turnover_total', 0)}.",
        f"Turnover/retorno: {turnover.get('turnover_to_return_ratio', 0)}.",
        "",
        "## Ativos problemáticos",
        _table(cost_result.get("cost_by_ticker", pd.DataFrame()), ["ticker", "trades_count", "total_cost_drag", "cost_drag_pct", "cost_drag_class"]),
        "",
        "## Fontes de sinal problemáticas",
        _table(cost_result.get("cost_by_signal_source", pd.DataFrame()), ["signal_source", "trades_count", "total_cost_drag", "cost_drag_pct", "cost_drag_class"]),
        "",
        "## Regras de saída problemáticas",
        _table(cost_result.get("cost_by_exit_reason", pd.DataFrame()), ["exit_reason", "trades_count", "total_cost_drag", "cost_drag_pct", "cost_drag_class"]),
        "",
        "## Break-even de custo",
        f"Custo máximo suportado: {breakeven.get('max_cost_bps_supported', 0)} bps.",
        f"Slippage máximo suportado: {breakeven.get('max_slippage_bps_supported', 0)} bps.",
        f"Redução de turnover para break-even: {breakeven.get('breakeven_turnover_reduction', 0)}.",
        "",
        "## Conclusão analítica",
        "Este diagnóstico identifica gargalos estruturais de custo/slippage. Parâmetros sugeridos por análise precisam passar por nova validação antes de qualquer observação recorrente.",
        "",
        "## Não recomendação",
        "Este relatório não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica parâmetros automaticamente.",
        "",
    ]
    return "\n".join(lines)


def save_cost_slippage_diagnostics_markdown(path: str | Path, cost_result: dict, turnover_result: dict | None = None, liquidity_result: dict | None = None, breakeven: dict | None = None) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_cost_slippage_diagnostics_markdown(cost_result, turnover_result, liquidity_result, breakeven), encoding="utf-8")
    return out
