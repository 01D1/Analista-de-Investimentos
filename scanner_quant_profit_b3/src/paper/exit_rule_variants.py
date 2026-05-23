"""Variantes simuladas de reducao de custo em regras de saida."""
from __future__ import annotations

import json

import pandas as pd


def _row(variant_id: str, title: str, description: str, expected_effect: str, overfitting_risk: str, **params) -> dict:
    return {
        "variant_id": variant_id,
        "variant_type": "exit",
        "title": title,
        "description": description,
        "parameters_json": json.dumps(params, ensure_ascii=False),
        "expected_effect": expected_effect,
        "overfitting_risk": overfitting_risk,
    }


def build_exit_rule_variants() -> pd.DataFrame:
    """Construir variantes simuladas de stop, take-profit, trailing e tempo."""
    rows = [
        _row("WIDER_STOP_LOSS", "Stop loss mais amplo", "Simula stop loss percentual mais amplo.", "Reduzir saídas por stop e custo de saída.", "MEDIO", stop_loss_pct=0.05),
        _row("TIGHTER_STOP_LOSS", "Stop loss mais curto", "Simula stop loss percentual mais curto.", "Reduzir perda bruta por trade.", "ALTO", stop_loss_pct=0.02),
        _row("WIDER_TAKE_PROFIT", "Take-profit mais amplo", "Simula alvo de ganho mais amplo.", "Reduzir frequência de saída por alvo.", "MEDIO", take_profit_pct=0.10),
        _row("LOWER_TAKE_PROFIT", "Take-profit menor", "Simula realização mais cedo.", "Testar menor permanência e menor drawdown.", "ALTO", take_profit_pct=0.04),
        _row("TRAILING_ONLY", "Apenas trailing stop", "Desativa stop fixo e take-profit, mantendo trailing.", "Reduzir saídas redundantes.", "MEDIO", stop_loss_pct=None, take_profit_pct=None, trailing_stop_pct=0.04, disable_stop_loss=True, disable_take_profit=True),
        _row("STOP_AND_TRAILING", "Stop e trailing", "Mantém stop fixo e trailing sem take-profit.", "Reduzir custo de take-profit e preservar proteção.", "MEDIO", stop_loss_pct=0.03, trailing_stop_pct=0.04, take_profit_pct=None, disable_take_profit=True),
        _row("ATR_STOP_ONLY", "Apenas ATR stop", "Usa stop por ATR simulado.", "Adaptar saída à volatilidade.", "ALTO", stop_loss_pct=None, take_profit_pct=None, trailing_stop_pct=None, atr_stop_multiplier=2.0, disable_take_profit=True),
        _row("NO_TAKE_PROFIT", "Sem take-profit", "Remove take-profit desta simulação.", "Reduzir custo de realização frequente.", "MEDIO", take_profit_pct=None, disable_take_profit=True),
        _row("TIME_EXIT_ONLY", "Saída por tempo", "Usa apenas saída por tempo com holding máximo.", "Controlar giro por calendário.", "ALTO", stop_loss_pct=None, take_profit_pct=None, trailing_stop_pct=None, max_holding_days=5, disable_take_profit=True, disable_stop_loss=True),
        _row("DELAYED_STOP_ACTIVATION", "Stop atrasado", "Ativa stop apenas após holding mínimo.", "Evitar stop precoce e custo de ruído.", "ALTO", min_holding_days_before_stop=3),
        _row("NO_SIMULATION_END_CLOSE", "Sem fechamento final", "Não força fechamento no último dia da janela.", "Isolar custo de fechamento de simulação.", "MEDIO", close_positions_at_end=False),
    ]
    return pd.DataFrame(rows)


def apply_exit_rule_variant(simulation_config: dict, variant: dict | pd.Series) -> dict:
    """Aplicar variante de regra de saída a uma configuracao simulada."""
    config = dict(simulation_config or {})
    raw = variant.get("parameters_json", "{}") if hasattr(variant, "get") else "{}"
    params = json.loads(raw or "{}") if isinstance(raw, str) else dict(raw or {})
    config.update(params)
    if params.get("disable_take_profit"):
        config["take_profit_pct"] = None
    if params.get("disable_stop_loss"):
        config["stop_loss_pct"] = None
    if params.get("max_holding_days") is not None:
        config["fixed_holding_days"] = params.get("max_holding_days")
    config["variant_id"] = variant.get("variant_id")
    config["variant_type"] = "exit"
    config["exit_mode"] = "advanced"
    return config
