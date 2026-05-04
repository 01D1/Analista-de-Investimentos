"""
intelligence.py — Camada de decisão do pipeline de valuation.

Transforma os resultados numéricos em decisão de investimento:
  - Recomendação: BUY / HOLD / SELL / AVOID
  - Score 0-100 composto por 3 dimensões
  - Nível de risco: BAIXO / MÉDIO / ALTO
  - Nível de confiança: ALTA / MÉDIA / BAIXA
  - Tese resumida em texto

Não modifica nenhum dado do pipeline — apenas lê e interpreta.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("pipeline.intelligence")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _f(value, default=None) -> Optional[float]:
    """Converte para float, retorna default se inválido/infinito."""
    try:
        v = float(value)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _last_n(df: pd.DataFrame, row: str, n: int = 3) -> list[float]:
    if df is None or df.empty or row not in df.index:
        return []
    serie = pd.to_numeric(df.loc[row], errors="coerce").dropna()
    return [float(v) for v in serie.tail(n).tolist() if np.isfinite(float(v))]


def _last(df: pd.DataFrame, row: str) -> Optional[float]:
    vals = _last_n(df, row, 1)
    return vals[0] if vals else None


def _cv(valores: list[float]) -> Optional[float]:
    """Coeficiente de variação — mede instabilidade histórica."""
    if len(valores) < 2:
        return None
    arr = np.array(valores)
    media = np.mean(arr)
    return float(np.std(arr) / abs(media)) if abs(media) > 1e-9 else None


# ─────────────────────────────────────────────────────────────────────────────
# Dimensão 1 — Score de Valuation (0-100)
# ─────────────────────────────────────────────────────────────────────────────

def _score_valuation(valuation: dict) -> tuple[float, list[str]]:
    """
    Avalia atratividade de preço via upside e TIR.

    Upside (60 pts):
      ≥ 50%  → 60  |  30–50% → 45–60  |  10–30% → 25–45
       0–10% → 0–25 |   < 0% → 0

    TIR (40 pts):
      ≥ 20% → 40  |  15–20% → 30–40  |  10–15% → 15–30
       5–10% → 0–15 |   < 5% → 0
    """
    det = []
    upside = _f(valuation.get("upside_on"), 0.0)
    tir = _f(valuation.get("tir_on"), 0.0)

    # Upside
    if upside >= 0.50:
        s_up = 60.0
    elif upside >= 0.30:
        s_up = 45.0 + (upside - 0.30) / 0.20 * 15.0
    elif upside >= 0.10:
        s_up = 25.0 + (upside - 0.10) / 0.20 * 20.0
    elif upside >= 0.0:
        s_up = upside / 0.10 * 25.0
    else:
        s_up = 0.0
    det.append(f"Upside ON: {upside:+.1%} → {s_up:.0f}/60 pts")

    # TIR
    if tir >= 0.20:
        s_tir = 40.0
    elif tir >= 0.15:
        s_tir = 30.0 + (tir - 0.15) / 0.05 * 10.0
    elif tir >= 0.10:
        s_tir = 15.0 + (tir - 0.10) / 0.05 * 15.0
    elif tir >= 0.05:
        s_tir = (tir - 0.05) / 0.05 * 15.0
    else:
        s_tir = 0.0
    det.append(f"TIR: {tir:.1%} → {s_tir:.0f}/40 pts")

    return round(min(100.0, s_up + s_tir), 1), det


# ─────────────────────────────────────────────────────────────────────────────
# Dimensão 2 — Score de Qualidade Fundamental (0-100)
# ─────────────────────────────────────────────────────────────────────────────

def _score_qualidade(
    dre: pd.DataFrame,
    indicadores: pd.DataFrame,
    tipo_empresa: str,
    qualidade_gate: dict,
) -> tuple[float, list[str]]:
    """
    Avalia solidez dos fundamentos: qualidade dos dados + ROE + consistência + indicador setorial.
    """
    det = []

    # Base: qualidade dos dados (0-35)
    gate = qualidade_gate.get("score", 50)
    s_base = gate * 0.35
    det.append(f"Qualidade dos dados: {gate}/100 → {s_base:.0f}/35 pts")
    score = s_base

    if indicadores is None or indicadores.empty:
        det.append("Sem indicadores históricos — qualidade limitada a dados brutos")
        return round(min(score + 10, 60.0), 1), det

    # ROE médio (0-35)
    roe_vals = _last_n(indicadores, "roe", 3)
    if roe_vals:
        roe = np.mean(roe_vals)
        limites = (0.18, 0.15, 0.10, 0.05) if tipo_empresa == "bank" else (0.20, 0.15, 0.10, 0.05)
        pontos = (35, 25, 14, 5)
        s_roe = 0
        for limite, pts in zip(limites, pontos):
            if roe >= limite:
                s_roe = pts
                break
        det.append(f"ROE médio 3 anos: {roe:.1%} → {s_roe}/35 pts")
        score += s_roe

    # Consistência histórica do lucro (0-15)
    lucros = _last_n(dre, "lucro_liquido", 5) if dre is not None else []
    if len(lucros) >= 3:
        negativos = sum(1 for v in lucros if v < 0)
        if negativos:
            s_consist = 0
            det.append(f"Lucros negativos: {negativos} ano(s) → 0/15 pts")
        else:
            cv = _cv(lucros)
            if cv is None:
                s_consist = 7
            elif cv < 0.15:
                s_consist = 15
            elif cv < 0.30:
                s_consist = 10
            elif cv < 0.50:
                s_consist = 5
            else:
                s_consist = 2
            cv_str = f"{cv:.2f}" if cv is not None else "?"
            det.append(f"Consistência lucro (CV={cv_str}) → {s_consist}/15 pts")
        score += s_consist

    # Indicador setorial (0-15)
    if tipo_empresa == "bank":
        inadim = _last(indicadores, "inadimplencia")
        nim = _last(indicadores, "nim")
        s_set = 0
        if inadim is not None:
            if inadim < 0.03:
                s_set += 8
            elif inadim < 0.05:
                s_set += 5
            elif inadim < 0.07:
                s_set += 2
        if nim is not None and 0.03 < nim < 0.12:
            s_set += 7
        det.append(
            f"NIM={f'{nim:.1%}' if nim is not None else '?'} / Inadim={f'{inadim:.1%}' if inadim is not None else '?'} → {s_set}/15 pts"
        )
        score += s_set
    else:
        m_ebitda = _last(indicadores, "margem_ebitda")
        if m_ebitda is not None:
            s_set = 15 if m_ebitda >= 0.25 else (10 if m_ebitda >= 0.15 else (5 if m_ebitda >= 0.08 else 0))
            det.append(f"Margem EBITDA={m_ebitda:.1%} → {s_set}/15 pts")
            score += s_set

    return round(min(score, 100.0), 1), det


# ─────────────────────────────────────────────────────────────────────────────
# Dimensão 3 — Risco (penalidade sobre o score final)
# ─────────────────────────────────────────────────────────────────────────────

def _avaliar_risco(
    valuation: dict,
    mercado: dict,
    avisos: list[str],
    qualidade_gate: dict,
    indicadores: pd.DataFrame,
    tipo_empresa: str,
) -> tuple[str, float, list[str]]:
    """
    Avalia risco e retorna (nivel, penalidade_score, fatores).
    Penalidade é descontada do score final: ALTO=-25, MÉDIO=-10, BAIXO=0.
    """
    pts = 0
    fatores = []

    # Problemas críticos nos dados
    criticos = qualidade_gate.get("critical", [])
    warnings_gate = qualidade_gate.get("warnings", [])
    if criticos:
        pts += 40
        fatores.append(f"{len(criticos)} problema(s) crítico(s) nos dados")
    elif warnings_gate:
        pts += min(10 * len(warnings_gate), 25)
        fatores.append(f"{len(warnings_gate)} aviso(s) de qualidade dos dados")

    # Avisos do valuation
    if avisos:
        pts += min(15 * len(avisos), 30)
        fatores.append(f"{len(avisos)} aviso(s) no valuation")

    # Beta
    beta = _f(mercado.get("beta_usar"), 0.85)
    if beta > 1.30:
        pts += 20
        fatores.append(f"Beta elevado ({beta:.2f})")
    elif beta > 1.00:
        pts += 10
        fatores.append(f"Beta moderado ({beta:.2f})")

    # Equity negativo
    if _f(valuation.get("equity_mm"), 1) <= 0:
        pts += 30
        fatores.append("Equity negativo — modelo instável")

    # TIR muito baixa
    tir = _f(valuation.get("tir_on"), 0)
    if tir < 0:
        pts += 20
        fatores.append(f"TIR negativa ({tir:.1%})")
    elif tir < 0.08:
        pts += 10
        fatores.append(f"TIR abaixo de 8% ({tir:.1%})")

    # Inadimplência alta (bancos)
    if tipo_empresa == "bank" and indicadores is not None and not indicadores.empty:
        inadim = _last(indicadores, "inadimplencia")
        if inadim is not None and inadim > 0.07:
            pts += 15
            fatores.append(f"Inadimplência elevada ({inadim:.1%})")

    if pts >= 50:
        return "ALTO", 25.0, fatores
    elif pts >= 20:
        return "MÉDIO", 10.0, fatores
    else:
        return "BAIXO", 0.0, fatores


# ─────────────────────────────────────────────────────────────────────────────
# Confiança
# ─────────────────────────────────────────────────────────────────────────────

def _avaliar_confianca(
    qualidade_gate: dict,
    avisos: list[str],
    sem_cvm: bool,
    indicadores: pd.DataFrame,
) -> tuple[str, str]:
    gate = qualidade_gate.get("score", 50)
    criticos = qualidade_gate.get("critical", [])
    tem_historico = indicadores is not None and not indicadores.empty

    if criticos or sem_cvm:
        return "BAIXA", "dados críticos ausentes ou CVM não consultada"
    if gate >= 80 and not avisos and tem_historico:
        return "ALTA", "dados completos, sem avisos, histórico disponível"
    if gate >= 60 and len(avisos) <= 1 and tem_historico:
        return "MÉDIA", "dados razoáveis com histórico disponível"
    if gate >= 50:
        return "MÉDIA", "qualidade de dados moderada"
    return "BAIXA", "múltiplos avisos ou dados insuficientes"


# ─────────────────────────────────────────────────────────────────────────────
# Geração de tese
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_tese(
    ticker: str,
    nome: str,
    recomendacao: str,
    score: int,
    risco: str,
    confianca: str,
    valuation: dict,
    mercado: dict,
    indicadores: pd.DataFrame,
    tipo_empresa: str,
    fatores_risco: list[str],
) -> str:
    upside = _f(valuation.get("upside_on"), 0.0)
    tir = _f(valuation.get("tir_on"), 0.0)
    pj = _f(valuation.get("preco_justo_on"), 0.0)
    pa = _f(mercado.get("preco"), 0.0)

    rec_base = recomendacao.split()[0]  # remove sufixo "(RISCO ALTO)" se houver
    if rec_base == "BUY":
        abertura = f"{nome} ({ticker}) apresenta desconto relevante frente ao valor justo estimado"
    elif rec_base == "HOLD":
        abertura = f"{nome} ({ticker}) negocia próximo ao valor justo, sem margem de segurança clara"
    else:
        abertura = f"{nome} ({ticker}) apresenta potencial limitado ou risco elevado no nível atual"

    val_txt = (
        f"Cotação de R$ {pa:.2f} vs. preço justo de R$ {pj:.2f} ({upside:+.1%} de upside), "
        f"TIR de {tir:.1%}."
        if pa > 0 and pj > 0
        else f"Upside de {upside:+.1%} e TIR de {tir:.1%}."
    )

    fund_parts = []
    if indicadores is not None and not indicadores.empty:
        roe = _last(indicadores, "roe")
        if roe is not None:
            fund_parts.append(f"ROE de {roe:.1%}")
        if tipo_empresa == "bank":
            inadim = _last(indicadores, "inadimplencia")
            if inadim is not None:
                fund_parts.append(f"inadimplência de {inadim:.1%}")
    fund_txt = f"Fundamentos: {', '.join(fund_parts)}." if fund_parts else ""

    risco_txt = f"Riscos: {'; '.join(fatores_risco[:2])}." if fatores_risco else ""
    score_txt = f"Score: {score}/100 | Risco: {risco} | Confiança: {confianca}."

    partes = [abertura + ". " + val_txt]
    if fund_txt:
        partes.append(fund_txt)
    if risco_txt:
        partes.append(risco_txt)
    partes.append(score_txt)
    return " ".join(partes)


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def analisar_valuation(
    *,
    ticker: str,
    nome: str,
    dados_empresa: Optional[dict],
    dre: pd.DataFrame,
    balanco: pd.DataFrame,
    indicadores: pd.DataFrame,
    mercado: dict,
    valuation: dict,
    avisos: list[str],
    qualidade: dict,
    sem_cvm: bool = False,
) -> dict:
    """
    Transforma resultados do valuation em decisão estruturada.

    Pesos do score final:
      50% — Score de Valuation  (upside + TIR)
      35% — Score de Qualidade  (ROE + consistência + indicador setorial)
      15% — Bônus de dados      (qualidade_gate score)
      − penalidade de risco     (ALTO=-25, MÉDIO=-10, BAIXO=0)

    Recomendação:
      BUY   → score ≥ 68 AND upside ≥ 25% AND TIR ≥ 13%
      HOLD  → score ≥ 52 AND upside ≥ 8%
      SELL  → upside < 0%
      AVOID → demais casos

    Returns dict com: ticker, nome, timestamp, recomendacao, score,
      risco, confianca, motivo_confianca, tese, detalhes.
    """
    tipo = (dados_empresa or {}).get("tipo_empresa", "general")

    sv, det_val = _score_valuation(valuation)
    sq, det_qual = _score_qualidade(dre, indicadores, tipo, qualidade)
    risco, penalidade, fatores = _avaliar_risco(valuation, mercado, avisos, qualidade, indicadores, tipo)

    gate = qualidade.get("score", 50)
    score_bruto = sv * 0.50 + sq * 0.35 + gate * 0.15
    score_final = round(max(0.0, min(100.0, score_bruto - penalidade)))

    upside = _f(valuation.get("upside_on"), 0.0)
    tir = _f(valuation.get("tir_on"), 0.0)

    if risco == "ALTO":
        if score_final >= 65 and upside > 0.30 and tir > 0.15:
            rec = "BUY (RISCO ALTO)"
        elif upside > 0:
            rec = "HOLD"
        else:
            rec = "AVOID"
    elif score_final >= 68 and upside >= 0.25 and tir >= 0.13:
        rec = "BUY"
    elif score_final >= 52 and upside >= 0.08:
        rec = "HOLD"
    elif upside < 0:
        rec = "SELL"
    else:
        rec = "AVOID"

    confianca, motivo_conf = _avaliar_confianca(qualidade, avisos, sem_cvm, indicadores)

    tese = _gerar_tese(
        ticker, nome, rec, score_final, risco, confianca,
        valuation, mercado, indicadores, tipo, fatores,
    )

    resultado = {
        "ticker": ticker,
        "nome": nome,
        "timestamp": datetime.now().isoformat(),
        "recomendacao": rec,
        "score": score_final,
        "risco": risco,
        "confianca": confianca,
        "motivo_confianca": motivo_conf,
        "tese": tese,
        "detalhes": {
            "score_valuation": sv,
            "score_qualidade": sq,
            "score_bruto": round(score_bruto, 1),
            "penalidade_risco": penalidade,
            "score_final": score_final,
            "upside_on": upside,
            "tir_on": tir,
            "fatores_risco": fatores,
            "breakdown_valuation": det_val,
            "breakdown_qualidade": det_qual,
        },
    }

    logger.info(
        "[intelligence] %s → %s | score=%d | risco=%s | confiança=%s",
        ticker, rec, score_final, risco, confianca,
    )
    return resultado
