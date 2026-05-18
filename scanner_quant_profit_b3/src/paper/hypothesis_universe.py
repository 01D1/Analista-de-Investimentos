"""Universo padrao de hipoteses em estudo para paper trading."""
from __future__ import annotations

import json

import pandas as pd


HYPOTHESIS_UNIVERSE_COLUMNS = [
    "hypothesis_id",
    "hypothesis_type",
    "title",
    "description",
    "target_scope",
    "parameters_json",
    "expected_effect",
    "risk_of_overfitting",
    "can_simulate",
]


def _row(hypothesis_id: str, title: str, description: str, target_scope: str, expected_effect: str, risk: str, **params) -> dict:
    return {
        "hypothesis_id": hypothesis_id,
        "hypothesis_type": hypothesis_id,
        "title": title,
        "description": description,
        "target_scope": target_scope,
        "parameters_json": json.dumps(params, ensure_ascii=False, sort_keys=True),
        "expected_effect": expected_effect,
        "risk_of_overfitting": risk,
        "can_simulate": True,
    }


def build_default_hypothesis_universe() -> pd.DataFrame:
    """Retorna hipoteses padrao para ranking multi-fonte, sem aplicacao automatica."""
    rows = [
        _row("REDUCE_VOLATILITY_EXPOSURE", "Reduzir exposição em volatilidade", "Reduz risco_pct e max_positions na simulação.", "portfolio", "Reduzir fragilidade e drawdown sem destruir retorno.", "MEDIO", risk_pct_multiplier=0.5, max_positions_delta=-1),
        _row("EXCLUDE_HIGH_FRAGILITY_ASSETS", "Excluir ativos frágeis", "Remove ativos com maior fragilidade observada na amostra simulada.", "asset", "Reduzir fragility score agregado.", "ALTO", bottom_score_quantile=0.20),
        _row("EXCLUDE_COST_DOMINATED_ASSETS", "Excluir ativos dominados por custo", "Remove ativos com baixa liquidez/custo alto quando o campo existir.", "asset", "Reduzir arrasto de custo.", "ALTO", max_cost_proxy_quantile=0.80),
        _row("LIMIT_ASSET_WEIGHT", "Limitar peso por ativo", "Reduz max_positions/risk_pct como proxy de concentração.", "portfolio", "Reduzir concentração e drawdown.", "MEDIO", risk_pct_multiplier=0.75, max_positions_delta=1),
        _row("LIMIT_SIGNAL_SOURCE", "Limitar fonte de sinal", "Mantém amostra alternada da fonte em estudo.", "source", "Reduzir fragilidade específica de fonte.", "MEDIO", keep_every_n=2),
        _row("EXCLUDE_LOW_SAMPLE_SIGNALS", "Excluir sinais de baixa amostra", "Remove tickers com poucas observações na janela.", "signal", "Evitar conclusões por amostra fraca.", "MEDIO", min_ticker_signals=3),
        _row("DISABLE_REBALANCING", "Desativar rebalanceamento", "Roda a simulação sem rebalanceamento.", "portfolio", "Reduzir custo operacional.", "BAIXO", enable_rebalancing=False),
        _row("REDUCE_REBALANCING_FREQUENCY", "Reduzir frequência de rebalanceamento", "Roda sem rebalanceamento como teste conservador.", "portfolio", "Reduzir custo e turnover.", "MEDIO", enable_rebalancing=False),
        _row("LIMIT_HIGH_SLIPPAGE_ASSETS", "Limitar ativos com slippage alto", "Remove ativos com proxy de liquidez fraca quando disponível.", "asset", "Reduzir sensibilidade a slippage.", "ALTO", min_volume_quantile=0.20),
        _row("BLOCK_DRAWDOWN_CONTRIBUTORS", "Bloquear contribuidores de drawdown", "Remove ativos com piores retornos recentes na janela.", "asset", "Reduzir drawdown sem sacrificar retorno.", "ALTO", worst_return_quantile=0.20),
        _row("REQUIRE_INTEGRATED_CONFIRMATION", "Exigir confirmação integrated", "Mantém sinais com ticker/data também presentes em integrated.", "confirmation", "Aumentar qualidade da amostra por convergência.", "MEDIO", confirmation_source="integrated"),
        _row("REQUIRE_TECHNICAL_CONFIRMATION", "Exigir confirmação technical", "Mantém sinais com ticker/data também presentes em technical.", "confirmation", "Reduzir sinais sem confirmação técnica.", "MEDIO", confirmation_source="technical"),
        _row("REQUIRE_QUANT_TECHNICAL_AGREEMENT", "Exigir acordo quant/técnico", "Mantém sinais com confirmação simultânea quant e technical.", "confirmation", "Buscar robustez entre fontes.", "MEDIO", confirmation_sources=["quant", "technical"]),
        _row("EXCLUDE_EVENT_RISK_SIGNALS", "Excluir risco de evento", "Remove sinais marcados com evento de risco quando o campo existir.", "event", "Reduzir fragilidade ligada a eventos.", "ALTO", excluded_event_contexts=["EVENTO_RECENTE", "EVENT_RISK"]),
        _row("EXCLUDE_LIQUIDITY_WEAK_REGIME", "Excluir regime de liquidez fraca", "Remove datas em regime de liquidez fraca quando regimes existirem.", "regime", "Reduzir slippage/custo em regime ruim.", "MEDIO", excluded_regimes=["LIQUIDEZ_FRACA", "BAIXA_LIQUIDEZ"]),
    ]
    return pd.DataFrame(rows, columns=HYPOTHESIS_UNIVERSE_COLUMNS)

