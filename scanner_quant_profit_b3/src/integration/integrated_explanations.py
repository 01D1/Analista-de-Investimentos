"""Explicações institucionais da inteligência integrada."""
from __future__ import annotations

import json

import pandas as pd


def _num(value, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(parsed) if pd.notna(parsed) else default


def _is_positive(value) -> bool:
    return _num(value) > 0


def generate_reasons_for(row) -> list[str]:
    reasons = []
    if _num(row.get("technical_score_final")) >= 65:
        reasons.append("Camada técnica com score técnico relevante.")
    if _num(row.get("quant_score")) >= 70:
        reasons.append("Camada quantitativa com score elevado.")
    if bool(row.get("valuation_available")) and _is_positive(row.get("upside_pct")):
        reasons.append("Valuation disponível com upside positivo.")
    if str(row.get("regime_governance_status", "")).upper() == "REGIME_OK":
        reasons.append("Regime atual sem bloqueio crítico.")
    if bool(row.get("option_available")):
        reasons.append("Há estrutura de opções para estudo analítico.")
    if str(row.get("risk_status", "")).upper() == "RISK_OK":
        reasons.append("Risk Engine sem bloqueio crítico no snapshot mais recente.")
    return reasons


def generate_reasons_against(row) -> list[str]:
    reasons = []
    blocked_values = [str(row.get(c, "")).upper() for c in ["technical_oos_status", "quant_governance_status", "option_oos_governance_status", "event_governance_status", "risk_status"]]
    if any("BLOCKED" in v or "BLOQUEADO" in v for v in blocked_values):
        reasons.append("Uma ou mais camadas estão bloqueadas por governança.")
    if not bool(row.get("valuation_available")):
        reasons.append("Valuation/fundamentos não encontrados ou insuficientes.")
    if _num(row.get("data_quality_score")) < 40:
        reasons.append("Qualidade de dados integrada baixa.")
    if str(row.get("event_governance_status", "")).upper() == "EVENT_COVERAGE_WEAK":
        reasons.append("Cobertura de eventos fraca ou insuficiente.")
    if _num(row.get("upside_pct")) < 0:
        reasons.append("Valuation indica assimetria fundamentalista negativa.")
    if "RISK_BLOCKED" in str(row.get("risk_status", "")).upper():
        reasons.append("Risk Engine indicou bloqueio por risco estimado.")
    elif str(row.get("risk_status", "")).upper() == "RISK_WARNING":
        reasons.append("Risk Engine indicou alerta de risco para observação.")
    return reasons


def generate_required_actions(row) -> list[str]:
    actions = []
    if not bool(row.get("valuation_available")):
        actions.append("Atualizar ou revisar valuation/fundamentos no pipeline externo.")
    if str(row.get("technical_oos_status", "")).upper().endswith("INSUFFICIENT_DATA"):
        actions.append("Ampliar histórico técnico e repetir walk-forward.")
    if str(row.get("event_governance_status", "")).upper() == "EVENT_COVERAGE_WEAK":
        actions.append("Melhorar cobertura de eventos/notícias antes de concluir sobre contexto.")
    if "RISK_BLOCKED" in str(row.get("risk_status", "")).upper():
        actions.append("Revisar volatilidade, VaR, liquidez e sizing sugerido para estudo antes de avançar a análise.")
    if not actions:
        actions.append("Manter em observação e validar em novas janelas.")
    return actions


def generate_integrated_explanation(row) -> str:
    ticker = row.get("ticker", "ativo")
    status = row.get("integrated_status", "SEM_DADOS_SUFICIENTES")
    tech = row.get("technical_status", "sem técnico")
    quant = row.get("quant_signal_type", "sem quant")
    valuation = "valuation disponível" if bool(row.get("valuation_available")) else "valuation não encontrado"
    regime = row.get("primary_regime", "regime indefinido")
    risk = row.get("risk_status", "risco não estimado")
    return (
        f"{ticker}: leitura integrada classificada como {status}. "
        f"Técnico: {tech}; quant: {quant}; {valuation}; regime: {regime}; risco: {risk}. "
        "A leitura é analítica, auditável e não constitui recomendação."
    )


def encode_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)
