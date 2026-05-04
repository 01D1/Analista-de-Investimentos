"""
quality_gate.py
===============
Valida sanidade dos dados normalizados antes de rodar o valuation.

Objetivo:
- Barrar casos claramente inválidos (dados vazios, relações impossíveis).
- Sinalizar possíveis problemas de escala/unidade.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _last_value(df: pd.DataFrame, row_name: str) -> float | None:
    """Retorna o valor mais recente de uma linha do DataFrame."""
    if df is None or df.empty or row_name not in df.index:
        return None
    serie = pd.to_numeric(df.loc[row_name], errors="coerce").dropna()
    if serie.empty:
        return None
    return float(serie.iloc[-1])


def avaliar_qualidade(
    dre_hist: pd.DataFrame,
    bp_hist: pd.DataFrame,
    tipo_empresa: str,
    permitir_sem_historico: bool = False,
) -> dict[str, Any]:
    """
    Avalia qualidade mínima dos dados para liberar o valuation.

    Returns:
        dict com:
        - score (0-100)
        - warnings (lista de alertas)
        - critical (lista de falhas críticas)
        - bloqueia_valuation (bool)
    """
    warnings: list[str] = []
    critical: list[str] = []
    score = 100

    if dre_hist is None or dre_hist.empty:
        if permitir_sem_historico:
            warnings.append("DRE histórica vazia (modo sem histórico habilitado).")
        else:
            critical.append("DRE histórica está vazia.")
    if bp_hist is None or bp_hist.empty:
        if permitir_sem_historico:
            warnings.append("Balanço histórico vazio (modo sem histórico habilitado).")
        else:
            critical.append("Balanço histórico está vazio.")

    if critical:
        return {
            "score": 0,
            "warnings": warnings,
            "critical": critical,
            "bloqueia_valuation": True,
        }

    # 1) Checagens básicas de balanço e plausibilidade
    ativo_total = _last_value(bp_hist, "ativo_total")
    passivo_total = _last_value(bp_hist, "passivo_total")
    lucro = _last_value(dre_hist, "lucro_liquido")

    if ativo_total is not None and ativo_total <= 0:
        critical.append("Ativo total <= 0 no último ano.")

    if ativo_total is not None and passivo_total is not None:
        if ativo_total == 0:
            critical.append("Ativo total zerado no último ano.")
        else:
            diff_pct = abs(ativo_total - passivo_total) / abs(ativo_total)
            if diff_pct > 0.05:
                critical.append("Ativo total e passivo total divergem mais de 5% no último ano.")
            elif diff_pct > 0.01:
                warnings.append("Ativo total e passivo total divergem entre 1% e 5% no último ano.")

    if lucro is not None and ativo_total is not None and abs(lucro) > abs(ativo_total):
        critical.append("Lucro líquido maior que ativo total no último ano (escala inconsistente).")

    # 2) Checagens de escala/sanidade por tipo
    if tipo_empresa == "bank":
        mfb = _last_value(dre_hist, "margem_financeira_bruta")
        ativos_remuneraveis = _last_value(bp_hist, "ativos_remuneraveis")
        pl_controladores = _last_value(bp_hist, "pl_controladores")

        if mfb is not None and ativos_remuneraveis is not None and ativos_remuneraveis > 0:
            nim = mfb / ativos_remuneraveis
            if nim > 0.30:
                critical.append("NIM > 30% no último ano (escala/unidade possivelmente incorreta).")
            elif nim < 0.005:
                warnings.append("NIM < 0,5% no último ano (possível problema de escala).")

        if lucro is not None and pl_controladores is not None and pl_controladores > 0:
            roe = lucro / pl_controladores
            if roe > 1.0:
                critical.append(
                    "ROE > 100% no último ano (escala/unidade possivelmente incorreta)."
                )
            elif roe < -0.5:
                warnings.append("ROE < -50% no último ano; revisar dados normalizados.")
    else:
        receita = _last_value(dre_hist, "receita_liquida")
        ebit = _last_value(dre_hist, "ebit")
        if receita is not None and receita != 0 and ebit is not None:
            margem_ebit = ebit / receita
            if margem_ebit > 0.8:
                warnings.append("Margem EBIT > 80% no último ano; validar mapeamento/escala.")
            if margem_ebit < -0.5:
                warnings.append("Margem EBIT < -50% no último ano; validar mapeamento/escala.")

    score -= 30 * len(critical)
    score -= 5 * len(warnings)
    score = max(score, 0)

    return {
        "score": score,
        "warnings": warnings,
        "critical": critical,
        "bloqueia_valuation": len(critical) > 0,
    }
