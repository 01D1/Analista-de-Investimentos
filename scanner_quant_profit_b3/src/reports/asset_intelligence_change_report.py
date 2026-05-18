"""Relatório Markdown do histórico de inteligência integrada por ativo."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.integration.asset_intelligence_history import summarize_asset_history


def _value(value, default: str = "-") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value)


def _num(value, decimals: int = 2) -> str:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return "-"
    return f"{float(parsed):.{decimals}f}"


def generate_asset_change_report(ticker: str, history_df: pd.DataFrame, diffs_df: pd.DataFrame) -> str:
    summary = summarize_asset_history(history_df)
    latest = history_df.iloc[-1] if history_df is not None and not history_df.empty else {}
    display_diffs = diffs_df.copy() if diffs_df is not None and not diffs_df.empty else pd.DataFrame()
    if not display_diffs.empty:
        sort_cols = [c for c in ["created_at", "id"] if c in display_diffs.columns]
        if sort_cols:
            display_diffs = display_diffs.sort_values(sort_cols, na_position="first")
        subset = [c for c in ["current_snapshot_id", "material_change_type"] if c in display_diffs.columns]
        if subset:
            display_diffs = display_diffs.drop_duplicates(subset=subset, keep="last")
    material = display_diffs[display_diffs["material_change"].fillna(False).astype(bool)] if not display_diffs.empty else pd.DataFrame()
    timeline = []
    if not display_diffs.empty:
        timeline_diffs = display_diffs.sort_values("current_created_at") if "current_created_at" in display_diffs.columns else display_diffs
        for _, row in timeline_diffs.iterrows():
            timeline.append(f"- {_value(row.get('current_created_at'))}: {_value(row.get('material_change_type'))} - {_value(row.get('explanation'))}")
    timeline_text = "\n".join(timeline) if timeline else "- Histórico insuficiente ou sem mudanças registradas."

    return f"""# {ticker} - Histórico de Inteligência Integrada

## 1. Situação Atual
- Último status: {_value(summary.get('latest_status'))}
- Último score: {_num(latest.get('integrated_score') if hasattr(latest, 'get') else None)}
- Governança: {_value(summary.get('latest_governance_status'))}
- Qualidade dos dados: {_num(latest.get('data_quality_score') if hasattr(latest, 'get') else None)}

## 2. Evolução do Score
- Score inicial: {_num(history_df.iloc[0].get('integrated_score')) if history_df is not None and not history_df.empty else '-'}
- Score atual: {_num(latest.get('integrated_score') if hasattr(latest, 'get') else None)}
- Tendência: {_value(summary.get('score_trend'))}

## 3. Mudanças de Status
- Mudanças de status: {summary.get('status_changes_count', 0)}
- Mudanças materiais: {len(material)}

## 4. Mudanças por Camada
- Técnico, quant, valuation, eventos, regimes e opções são avaliados em cada diff salvo.
- Consulte a linha do tempo para o detalhamento textual das mudanças.

## 5. Governança
- Bloqueios de governança observados: {summary.get('governance_blocks_count', 0)}
- Status de governança atual: {_value(summary.get('latest_governance_status'))}

## 6. Linha do Tempo
{timeline_text}

## 7. Conclusão Analítica
Este relatório mostra como a leitura integrada mudou ao longo do tempo e quais camadas explicam essa mudança. A análise é auditável, depende da qualidade dos dados disponíveis e não constitui recomendação financeira ou chamada operacional.
"""


def save_asset_change_report(ticker: str, history_df: pd.DataFrame, diffs_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ticker}_historico_inteligencia_integrada.md"
    path.write_text(generate_asset_change_report(ticker, history_df, diffs_df), encoding="utf-8")
    return path
