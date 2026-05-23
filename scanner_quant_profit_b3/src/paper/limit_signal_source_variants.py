"""Variações paramétricas da hipótese LIMIT_SIGNAL_SOURCE."""
from __future__ import annotations

import json

import pandas as pd


VARIANT_COLUMNS = [
    "variant_id",
    "hypothesis_id",
    "title",
    "description",
    "parameters_json",
    "target_source",
    "cost_limit",
    "slippage_limit",
    "regime_filter",
    "asset_filter",
    "required_confirmations",
    "expected_effect",
    "overfitting_risk",
]


def _row(variant_id: str, title: str, description: str, params: dict, target_source: str = "", cost_limit: float | None = None, slippage_limit: float | None = None, regime_filter: str = "", asset_filter: str = "", required_confirmations: int = 0, expected_effect: str = "reduzir fragilidade sem destruir retorno", overfitting_risk: str = "MEDIUM") -> dict:
    return {
        "variant_id": variant_id,
        "hypothesis_id": "LIMIT_SIGNAL_SOURCE",
        "title": title,
        "description": description,
        "parameters_json": json.dumps(params, ensure_ascii=False, default=str),
        "target_source": target_source,
        "cost_limit": cost_limit,
        "slippage_limit": slippage_limit,
        "regime_filter": regime_filter,
        "asset_filter": asset_filter,
        "required_confirmations": required_confirmations,
        "expected_effect": expected_effect,
        "overfitting_risk": overfitting_risk,
    }


def build_limit_signal_source_variants() -> pd.DataFrame:
    """Monta variações em estudo para calibração paramétrica.

    As variações são apenas simulação/investigação; nenhuma delas é aplicada
    automaticamente ao score, ao ranking ou a ordens.
    """
    rows = [
        _row("LIMIT_QUANT_ONLY", "Limitar quant", "Limita exposição quando a fonte quant domina a carteira.", {"action": "limit_source", "keep_every_n": 2}, target_source="quant", overfitting_risk="MEDIUM"),
        _row("LIMIT_TECHNICAL_ONLY", "Limitar technical", "Limita exposição quando technical tem baixa robustez.", {"action": "limit_source", "keep_every_n": 2}, target_source="technical", overfitting_risk="MEDIUM"),
        _row("LIMIT_INTEGRATED_ONLY", "Limitar integrated", "Limita exposição quando integrated tem baixa amostra.", {"action": "limit_source", "keep_every_n": 2}, target_source="integrated", overfitting_risk="HIGH"),
        _row("REQUIRE_TWO_SOURCE_CONFIRMATION", "Exigir duas fontes", "Permite sinal apenas quando ao menos duas fontes concordam.", {"action": "require_confirmations"}, required_confirmations=2, overfitting_risk="MEDIUM"),
        _row("REQUIRE_INTEGRATED_CONFIRMATION", "Exigir integrated", "Permite sinal apenas quando integrated confirma a data/ativo.", {"action": "require_integrated"}, target_source="integrated", required_confirmations=1, overfitting_risk="MEDIUM"),
        _row("EXCLUDE_SOURCE_WITH_HIGH_COST_DRAG", "Excluir fonte com custo alto", "Exclui fonte quando cost drag estimado excede o limite.", {"action": "cost_drag_filter"}, cost_limit=0.0020, overfitting_risk="LOW"),
        _row("LIMIT_SOURCE_BY_REGIME", "Limitar por regime", "Limita fonte em regimes frágeis.", {"action": "regime_filter", "fragile_regimes": ["ALTA_VOLATILIDADE", "LIQUIDEZ_FRACA", "BAIXA_TENDENCIAL"]}, regime_filter="ALTA_VOLATILIDADE,LIQUIDEZ_FRACA,BAIXA_TENDENCIAL", overfitting_risk="MEDIUM"),
        _row("LIMIT_SOURCE_BY_ASSET", "Limitar por ativo", "Limita fonte em ativos com fragility_score alto.", {"action": "asset_filter", "max_assets": 3}, asset_filter="FRAGILE_ASSETS", overfitting_risk="HIGH"),
        _row("LIMIT_SOURCE_BY_SLIPPAGE", "Limitar por slippage", "Bloqueia fonte quando slippage médio excede o limite.", {"action": "slippage_filter"}, slippage_limit=0.0015, overfitting_risk="LOW"),
        _row("LIMIT_SOURCE_BY_TURNOVER", "Limitar por turnover", "Bloqueia fonte quando turnover associado excede limite.", {"action": "turnover_filter", "turnover_limit": 0.35}, overfitting_risk="MEDIUM"),
    ]
    return pd.DataFrame(rows, columns=VARIANT_COLUMNS)
