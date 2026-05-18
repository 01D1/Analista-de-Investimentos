"""Relatório Markdown da inteligência integrada por ativo."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _value(row, key: str, default: str = "-") -> str:
    value = row.get(key, default) if hasattr(row, "get") else default
    if value is None or pd.isna(value):
        return default
    return str(value)


def _num(row, key: str, suffix: str = "", decimals: int = 2) -> str:
    value = pd.to_numeric(pd.Series([row.get(key) if hasattr(row, "get") else None]), errors="coerce").iloc[0]
    if pd.isna(value):
        return "-"
    return f"{float(value):.{decimals}f}{suffix}"


def _list_from_json(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None or pd.isna(value):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except json.JSONDecodeError:
            return [value] if value else []
    return [str(value)]


def _bullets(values: list[str]) -> str:
    if not values:
        return "- Sem itens registrados."
    return "\n".join(f"- {v}" for v in values)


def generate_asset_intelligence_report(row) -> str:
    """Gera relatório Markdown institucional. Não contém recomendação operacional."""
    ticker = _value(row, "ticker", "ATIVO")
    reasons_for = _list_from_json(row.get("reasons_for") if hasattr(row, "get") else None)
    reasons_against = _list_from_json(row.get("reasons_against") if hasattr(row, "get") else None)
    actions = _list_from_json(row.get("required_actions") if hasattr(row, "get") else None)

    return f"""# {ticker} - Relatório Integrado

## 1. Resumo Executivo
- Status integrado: {_value(row, "integrated_status")}
- Score integrado: {_num(row, "integrated_score")}
- Confiança: {_value(row, "integrated_confidence")}
- Governança integrada: {_value(row, "integrated_governance_status")}
- Síntese: {_value(row, "explanation")}

## 2. Análise Técnica Quantitativa
- Setup técnico: {_value(row, "top_technical_setup")}
- Score técnico: {_num(row, "technical_score_final")}
- Status técnico: {_value(row, "technical_status")}
- Governança técnica: {_value(row, "technical_governance_status")}
- Validação OOS: {_value(row, "technical_oos_status")}

## 3. Sinal Quantitativo
- Score quant: {_num(row, "quant_score")}
- Tipo de sinal: {_value(row, "quant_signal_type")}
- Governança quant: {_value(row, "quant_governance_status")}

## 4. Valuation e Fundamentos
- Valuation disponível: {_value(row, "valuation_available")}
- Preço justo: {_num(row, "fair_value")}
- Upside: {_num(row, "upside_pct", suffix="%")}
- Método: {_value(row, "valuation_method")}
- Confiança: {_num(row, "valuation_confidence")}

## 5. Eventos e Notícias
- Evento recente: {_value(row, "has_recent_event")}
- Tipo de evento: {_value(row, "event_type")}
- Contexto: {_value(row, "event_context_type")}
- Impacto: {_num(row, "event_impact_score")}
- Cobertura: {_value(row, "event_coverage_quality")}

## 6. Regime de Mercado
- Regime principal: {_value(row, "primary_regime")}
- Tendência: {_value(row, "trend_regime")}
- Volatilidade: {_value(row, "volatility_regime")}
- Liquidez: {_value(row, "liquidity_regime")}

## 7. Opções e Estruturas
- Opções disponíveis: {_value(row, "option_available")}
- Estrutura para estudo: {_value(row, "best_option_structure_type")}
- Score da estrutura: {_num(row, "option_structure_score")}
- Liquidez: {_num(row, "option_liquidity_score")}
- Governança OOS: {_value(row, "option_oos_governance_status")}

## 8. Risco e Volatilidade
- Regime de volatilidade: {_value(row, "volatility_regime")}
- Volatilidade ensemble: {_num(row, "ensemble_vol")}
- VaR 95%: {_num(row, "var_95")}
- Expected Shortfall 95%: {_num(row, "expected_shortfall_95")}
- Sizing sugerido para estudo: {_num(row, "recommended_size", decimals=0)}
- Valor sugerido para estudo: {_num(row, "recommended_position_value")}
- Fator limitante: {_value(row, "risk_limiting_factor")}
- Status de risco: {_value(row, "risk_status")}
- Explicação de risco: {_value(row, "risk_explanation")}

## 9. Governança Integrada
### Motivos Favoráveis
{_bullets(reasons_for)}

### Motivos Contrários
{_bullets(reasons_against)}

### Ações Necessárias
{_bullets(actions)}

## 10. Conclusão Analítica
Este relatório consolida camadas quantitativas, técnicas, eventos, regimes, opções, valuation e risco para estudo auditável do ativo. A leitura é diagnóstica, pode conter dados insuficientes e não constitui recomendação financeira ou chamada operacional.
"""


def save_asset_intelligence_report(row, output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ticker = _value(row, "ticker", "ATIVO").replace("/", "_")
    path = out_dir / f"{ticker}_relatorio_integrado.md"
    path.write_text(generate_asset_intelligence_report(row), encoding="utf-8")
    return path
