"""Relatorio Markdown do diagnostico fino de custos."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df is None or df.empty:
        return "Evidência insuficiente."
    return df[[c for c in cols if c in df.columns]].head(20).to_markdown(index=False)


def generate_fine_cost_diagnostics_markdown(result: dict) -> str:
    lifecycle_summary = result.get("lifecycle_summary", {})
    rebalance_summary = result.get("rebalance", {}).get("summary", {})
    unknown_summary = result.get("unknown", {}).get("summary", {})
    metadata_fixes = result.get("metadata_fixes") or []
    rebalance_suggestions = result.get("rebalance_suggestions") or []
    missing = unknown_summary.get("missing_fields_summary", {})
    if isinstance(missing, str):
        try:
            missing = json.loads(missing)
        except json.JSONDecodeError:
            missing = {}
    lines = [
        "# Diagnóstico Fino de Custos",
        "",
        "## Resumo",
        "Diagnóstico simulado para atribuir origem de custo sem reescrever histórico.",
        f"Entrada: {lifecycle_summary.get('entry_cost_pct', 0):.4f} do custo atribuído.",
        f"Saída: {lifecycle_summary.get('exit_cost_pct', 0):.4f} do custo atribuído.",
        f"Rebalanceamento: {lifecycle_summary.get('rebalance_cost_pct', 0):.4f} do custo atribuído.",
        "",
        "## Custo por ciclo da posição",
        _table(result.get("lifecycle", pd.DataFrame()), ["lifecycle_id", "ticker", "entry_date", "exit_date", "entry_cost", "exit_cost", "rebalance_cost", "total_cost", "cost_to_pnl_ratio"]),
        "",
        "## Entrada vs saída vs rebalance",
        f"Custo médio de entrada: {lifecycle_summary.get('avg_entry_cost', 0):.4f}.",
        f"Custo médio de saída: {lifecycle_summary.get('avg_exit_cost', 0):.4f}.",
        f"Custo médio de rebalance: {lifecycle_summary.get('avg_rebalance_cost', 0):.4f}.",
        "",
        "## Rebalanceamento",
        f"Classe: {rebalance_summary.get('rebalance_cost_class', 'REBALANCE_DATA_INSUFFICIENT')}.",
        f"Custo total de rebalanceamento: {rebalance_summary.get('rebalance_cost_total', 0)}.",
        _table(result.get("rebalance", {}).get("rebalance_cost_by_ticker", pd.DataFrame()), ["ticker", "rebalance_orders_count", "rebalance_cost_total", "rebalance_slippage_total"]),
        "",
        "## Regras de saída",
        _table(result.get("exit_rules", pd.DataFrame()), ["exit_rule", "exit_count", "gross_pnl", "net_pnl", "cost_drag", "cost_to_pnl_ratio", "exit_rule_cost_class"]),
        "",
        "## Custos UNKNOWN",
        f"Ordens com metadado ausente/UNKNOWN: {unknown_summary.get('unknown_orders_count', 0)}.",
        f"Custo atribuído a UNKNOWN/metadado ausente: {unknown_summary.get('unknown_cost_total', 0)}.",
        "",
        "## Problemas de metadata",
        _table(pd.DataFrame([{"field": k, "count": v} for k, v in missing.items()]), ["field", "count"]),
        "",
        "## Sugestões analíticas",
        "\n".join(f"- {item}" for item in (metadata_fixes + rebalance_suggestions)) or "Evidência insuficiente.",
        "",
        "## Não recomendação",
        "Este relatório não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica calibração automaticamente.",
        "",
    ]
    return "\n".join(lines)


def save_fine_cost_diagnostics_markdown(path: str | Path, result: dict) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_fine_cost_diagnostics_markdown(result), encoding="utf-8")
    return out
