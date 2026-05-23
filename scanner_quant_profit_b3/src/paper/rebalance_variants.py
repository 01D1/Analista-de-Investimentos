"""Variantes simuladas de reducao de custo de rebalanceamento."""
from __future__ import annotations

import json

import pandas as pd


def _row(variant_id: str, title: str, description: str, expected_effect: str, overfitting_risk: str, **params) -> dict:
    return {
        "variant_id": variant_id,
        "variant_type": "rebalance",
        "title": title,
        "description": description,
        "parameters_json": json.dumps(params, ensure_ascii=False),
        "expected_effect": expected_effect,
        "overfitting_risk": overfitting_risk,
    }


def build_rebalance_variants() -> pd.DataFrame:
    """Construir variantes de rebalanceamento simulado em estudo."""
    rows = [
        _row("DISABLE_REBALANCE", "Desativar rebalanceamento", "Simula sem rebalanceamento.", "Reduzir custo de rebalanceamento.", "BAIXO", enable_rebalancing=False),
        _row("WEEKLY_REBALANCE", "Rebalanceamento semanal", "Mantém rebalanceamento semanal.", "Reduzir frequência frente a cenários diários.", "BAIXO", enable_rebalancing=True, rebalance_frequency="WEEKLY"),
        _row("THRESHOLD_REBALANCE_5PCT", "Threshold 5%", "Só rebalanceia diferenças de peso acima de 5%.", "Cortar micro ajustes.", "MEDIO", enable_rebalancing=True, rebalance_min_delta_weight=0.05),
        _row("THRESHOLD_REBALANCE_10PCT", "Threshold 10%", "Só rebalanceia diferenças de peso acima de 10%.", "Cortar ajustes pequenos com mais força.", "MEDIO", enable_rebalancing=True, rebalance_min_delta_weight=0.10),
        _row("VOL_ADJUSTED_REBALANCE", "Rebalance por volatilidade", "Mantém rebalance por risco com frequência semanal.", "Evitar giro sem mudança de risco.", "MEDIO", enable_rebalancing=True, rebalance_frequency="WEEKLY", use_regime_adjustment=False),
        _row("REGIME_BLOCKED_REBALANCE", "Bloqueio por regime", "Bloqueia rebalanceamento nesta simulação conservadora.", "Evitar custo em regimes frágeis.", "ALTO", enable_rebalancing=False, regime_blocked=True),
        _row("LIQUIDITY_FILTERED_REBALANCE", "Filtro de liquidez", "Usa threshold de peso para reduzir ordens pequenas em liquidez fraca.", "Reduzir slippage de rebalanceamento.", "MEDIO", enable_rebalancing=True, rebalance_min_delta_weight=0.05, liquidity_filtered=True),
        _row("MAX_REBALANCE_TURNOVER", "Limite de turnover", "Limita notional de rebalance por ciclo.", "Conter custo máximo por evento.", "MEDIO", enable_rebalancing=True, max_rebalance_turnover_pct=0.05),
    ]
    return pd.DataFrame(rows)


def apply_rebalance_variant(simulation_config: dict, variant: dict | pd.Series) -> dict:
    """Aplicar variante em uma configuracao simulada."""
    config = dict(simulation_config or {})
    raw = variant.get("parameters_json", "{}") if hasattr(variant, "get") else "{}"
    params = json.loads(raw or "{}") if isinstance(raw, str) else dict(raw or {})
    config.update(params)
    config["variant_id"] = variant.get("variant_id")
    config["variant_type"] = "rebalance"
    config.setdefault("exit_mode", "advanced")
    return config
