"""Modelo tabular do snapshot integrado por ativo."""
from __future__ import annotations

import pandas as pd


ASSET_INTELLIGENCE_COLUMNS = [
    "ticker",
    "company_name",
    "sector",
    "subsector",
    "trade_date",
    "market_price",
    "technical_score_final",
    "technical_status",
    "top_technical_setup",
    "technical_setup_score",
    "technical_setup_confidence",
    "technical_governance_status",
    "technical_oos_status",
    "technical_explanation",
    "quant_score",
    "quant_signal_type",
    "quant_signal_confidence",
    "quant_governance_status",
    "quant_explanation",
    "valuation_available",
    "fair_value",
    "upside_pct",
    "valuation_method",
    "valuation_confidence",
    "fundamental_quality_score",
    "financial_health_score",
    "profitability_score",
    "growth_score",
    "leverage_score",
    "valuation_governance_status",
    "has_recent_event",
    "event_type",
    "event_context_type",
    "event_impact_score",
    "event_coverage_quality",
    "event_governance_status",
    "primary_regime",
    "trend_regime",
    "volatility_regime",
    "liquidity_regime",
    "risk_regime",
    "regime_governance_status",
    "option_available",
    "best_option_structure_type",
    "option_structure_score",
    "option_oos_governance_status",
    "option_liquidity_score",
    "option_execution_quality",
    "option_explanation",
    "ensemble_vol",
    "var_95",
    "expected_shortfall_95",
    "recommended_size",
    "recommended_position_value",
    "risk_status",
    "risk_limiting_factor",
    "risk_explanation",
    "integrated_score",
    "integrated_status",
    "integrated_confidence",
    "data_quality_score",
    "governance_blocked",
    "integrated_governance_status",
    "reasons_for",
    "reasons_against",
    "required_actions",
    "explanation",
    "metadata_json",
]


INTEGRATED_STATUSES = {
    "ALTA_CONVERGENCIA_ANALITICA",
    "ASSIMETRIA_A_INVESTIGAR",
    "APENAS_MONITORAR",
    "DIVERGENCIA_TECNICA_VALUATION",
    "DIVERGENCIA_QUANT_TECNICA",
    "BLOQUEADO_GOVERNANCA",
    "BLOQUEADO_DADOS_INSUFICIENTES",
    "BLOQUEADO_EVENTO_CONTRA",
    "BLOQUEADO_LIQUIDEZ",
    "SEM_DADOS_SUFICIENTES",
}


def empty_asset_intelligence_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=ASSET_INTELLIGENCE_COLUMNS)


def normalize_asset_intelligence_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ASSET_INTELLIGENCE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[ASSET_INTELLIGENCE_COLUMNS]
