"""Relatorio Markdown de fragilidade da carteira simulada."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _table(df: pd.DataFrame | None, limit: int = 25) -> str:
    if df is None or df.empty:
        return "_Sem dados salvos._"
    return df.head(limit).to_markdown(index=False)


def _meta(summary: dict) -> dict:
    try:
        return json.loads(summary.get("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def generate_paper_fragility_report(
    summary: dict,
    asset_df: pd.DataFrame,
    signal_source_df: pd.DataFrame,
    drawdown_df: pd.DataFrame,
    cost_df: pd.DataFrame | None = None,
) -> str:
    meta = _meta(summary)
    gov = meta.get("governance", {})
    return f"""# Relatório de Fragilidade da Carteira Simulada

## Resumo

- Status: {summary.get("status", "-")}
- Governança: {summary.get("governance_status", "-")}
- Trades simulados: {summary.get("total_trades", 0)}
- P&L líquido simulado: {summary.get("total_net_pnl", 0)}
- Fragility score: {summary.get("fragility_score", "-")}
- Classe: {summary.get("fragility_class", "-")}

## Fragilidade por Ativo

{_table(asset_df)}

## Fragilidade por Fonte de Sinal

{_table(signal_source_df)}

## Custos e Slippage

{_table(cost_df)}

## Drawdowns

{_table(drawdown_df)}

## Governança

- Motivos favoráveis: {", ".join(gov.get("reasons_for", []) or []) or "-"}
- Motivos contrários: {", ".join(gov.get("reasons_against", []) or []) or "-"}
- Ações de investigação: {", ".join(gov.get("required_actions", []) or []) or "-"}

## Ações de Investigação

- Investigar ativos com contribuição negativa e alto custo/slippage.
- Revisar fonte em observação com baixa taxa de acerto.
- Mapear drawdowns concentrados antes de qualquer uso operacional.

## Não recomendação

Este relatório descreve apenas simulação e diagnóstico. Não executa ordens reais, não recomenda compra ou venda e não altera score ou ranking principal.
"""


def save_paper_fragility_report(
    output_dir: str | Path,
    summary: dict,
    asset_df: pd.DataFrame,
    signal_source_df: pd.DataFrame,
    drawdown_df: pd.DataFrame,
    cost_df: pd.DataFrame | None = None,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "paper_fragility_report.md"
    path.write_text(generate_paper_fragility_report(summary, asset_df, signal_source_df, drawdown_df, cost_df), encoding="utf-8")
    return path
