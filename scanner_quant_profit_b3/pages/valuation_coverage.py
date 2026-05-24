"""
pages/valuation_coverage.py

Matriz de cobertura operacional de valuation.
Exibe status, gaps e plano de ação por ticker da watchlist.

Baseado em: src/fundamentals/valuation_coverage.py
Filho de: M014-S01 (coverage audit)
Pai de: M014-S03 (arquitetura de ingestão) / S04 (pipeline de CVM)
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── resolve project root ──
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import streamlit as st

from src.fundamentals.valuation_coverage import (
    CoverageStatus,
    CoverageMatrix,
    classify_coverage,
)

# ──────────────────────────────────────────────
#  Config da página
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Cobertura de Valuation",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Matriz de Cobertura de Valuation")
st.caption("M014-S02 · Status real por ticker · Baseado em auditoria S01")

# ──────────────────────────────────────────────
#  Init
# ──────────────────────────────────────────────

matrix = CoverageMatrix()

# ──────────────────────────────────────────────
#  Resumo — contagens
# ──────────────────────────────────────────────

st.subheader("Visão Geral")

counts = matrix.summary_counts()

col_summary1, col_summary2, col_summary3, col_summary4, col_summary5 = st.columns(5)

status_chip = {
    CoverageStatus.NEEDS_DATA: ("🔴 NEEDS_DATA", "background-color: #2d1f1f; color: #ff8080"),
    CoverageStatus.EMPTY: ("🟤 EMPTY", "background-color: #1f1f2d; color: #8080ff"),
    CoverageStatus.PARTIAL: ("🟡 PARTIAL", "background-color: #2d2d1f; color: #ffff80"),
    CoverageStatus.NEEDS_MODEL: ("🟠 NEEDS_MODEL", "background-color: #2d251f; color: #ffbf80"),
    CoverageStatus.READY: ("🟢 READY", "background-color: #1f2d1f; color: #80ff80"),
}

total = sum(counts.values())
col_summary1.metric("Total watchlist", total)
col_summary2.metric("🟢 READY", counts.get("ready", 0))
col_summary3.metric("🟡 PARTIAL", counts.get("partial", 0))
col_summary4.metric("🟠 NEEDS_MODEL", counts.get("needs_model", 0))
col_summary5.metric("🔴 NEEDS_DATA", counts.get("needs_data", 0))

# ──────────────────────────────────────────────
#  Chips por ticker
# ──────────────────────────────────────────────

st.divider()
st.subheader("Status por Ticker")

CHIP_STYLE = {
    CoverageStatus.NEEDS_DATA: "background-color:#7f1d1d;color:white;font-weight:bold;padding:4px 12px;border-radius:20px;display:inline-block",
    CoverageStatus.EMPTY: "background-color:#1e3a5f;color:white;font-weight:bold;padding:4px 12px;border-radius:20px;display:inline-block",
    CoverageStatus.PARTIAL: "background-color:#713f12;color:white;font-weight:bold;padding:4px 12px;border-radius:20px;display:inline-block",
    CoverageStatus.NEEDS_MODEL: "background-color:#7c2d12;color:white;font-weight:bold;padding:4px 12px;border-radius:20px;display:inline-block",
    CoverageStatus.READY: "background-color:#14532d;color:white;font-weight:bold;padding:4px 12px;border-radius:20px;display:inline-block",
}

LABEL = {
    CoverageStatus.NEEDS_DATA: "🔴 NEEDS_DATA",
    CoverageStatus.EMPTY: "🟤 EMPTY",
    CoverageStatus.PARTIAL: "🟡 PARTIAL",
    CoverageStatus.NEEDS_MODEL: "🟠 NEEDS_MODEL",
    CoverageStatus.READY: "🟢 READY",
}

CHIP_COLOR = {
    CoverageStatus.NEEDS_DATA: "red",
    CoverageStatus.EMPTY: "blue",
    CoverageStatus.PARTIAL: "yellow",
    CoverageStatus.NEEDS_MODEL: "orange",
    CoverageStatus.READY: "green",
}

items = matrix.items()

for ticker, status in items:
    label = LABEL[status]
    color = CHIP_COLOR[status]
    st.code(f"{ticker:8s}  ➜  {label}", language=None)

st.divider()

# ──────────────────────────────────────────────
#  Tabela detalhada
# ──────────────────────────────────────────────

st.subheader("Detalhamento por Ticker")

# Dados reais do audit S01
TICKER_DETAIL = {
    "BBAS3": {
        "tipo": "BANK",
        "ai": "✅",
        "cvm_docs": "121",
        "cvm_trace": "6100",
        "discrepancy": "❌",
        "fair_value": "R$ 64,84",
        "valuation_available": "✅",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "5",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_METHOD_MISSING · FQS_MISSING",
    },
    "BBDC4": {
        "tipo": "BANK",
        "ai": "✅",
        "cvm_docs": "125",
        "cvm_trace": "6100",
        "discrepancy": "❌",
        "fair_value": "❌",
        "valuation_available": "✅ (flag=1, sem FV)",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "6",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · FAIR_VALUE_MISSING · VALUATION_METHOD_MISSING · FQS_MISSING",
    },
    "BPAC11": {
        "tipo": "BANK",
        "ai": "❌",
        "cvm_docs": "0",
        "cvm_trace": "6100 (discrepancy!)",
        "discrepancy": "⚠️ SIM",
        "fair_value": "❌",
        "valuation_available": "❌ (sem AI)",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "2",
        "gaps": "AI_ENTRY_MISSING · CVM_DOCS_MISSING",
    },
    "ITUB4": {
        "tipo": "BANK",
        "ai": "✅",
        "cvm_docs": "125",
        "cvm_trace": "6100",
        "discrepancy": "❌",
        "fair_value": "R$ 73,69",
        "valuation_available": "✅",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "5",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_METHOD_MISSING · FQS_MISSING",
    },
    "PETR4": {
        "tipo": "ENERGY",
        "ai": "✅",
        "cvm_docs": "131",
        "cvm_trace": "6100",
        "discrepancy": "❌",
        "fair_value": "R$ 81,12",
        "valuation_available": "✅",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "5",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_METHOD_MISSING · FQS_MISSING",
    },
    "SANB11": {
        "tipo": "INDUSTRIAL",
        "ai": "❌",
        "cvm_docs": "0",
        "cvm_trace": "6100 (discrepancy!)",
        "discrepancy": "⚠️ SIM",
        "fair_value": "❌",
        "valuation_available": "❌ (sem AI)",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "2",
        "gaps": "AI_ENTRY_MISSING · CVM_DOCS_MISSING",
    },
    "SUZB3": {
        "tipo": "COMMODITY",
        "ai": "✅",
        "cvm_docs": "0",
        "cvm_trace": "6100 (discrepancy!)",
        "discrepancy": "⚠️ SIM",
        "fair_value": "❌",
        "valuation_available": "❌ (flag=0)",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "7",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_FLAG_ABSENT · VALUATION_METHOD_MISSING · FQS_MISSING · CVM_DOCS_MISSING",
    },
    "VALE3": {
        "tipo": "COMMODITY",
        "ai": "✅",
        "cvm_docs": "0",
        "cvm_trace": "0 (sem coleta)",
        "discrepancy": "⚠️ SEM TRACE",
        "fair_value": "❌",
        "valuation_available": "❌ (flag=0)",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "7",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_FLAG_ABSENT · VALUATION_METHOD_MISSING · FQS_MISSING · CVM_DOCS_MISSING",
    },
    "WEGE3": {
        "tipo": "INDUSTRIAL",
        "ai": "✅",
        "cvm_docs": "124",
        "cvm_trace": "6100",
        "discrepancy": "❌",
        "fair_value": "R$ 40,16",
        "valuation_available": "✅",
        "valuation_method": "❌",
        "fqs": "❌",
        "sector": "❌",
        "company_name": "❌",
        "ai_market_price": "❌",
        "gap_count": "5",
        "gaps": "COMPANY_NAME_MISSING · SECTOR_MISSING · MARKET_PRICE_MISSING · VALUATION_METHOD_MISSING · FQS_MISSING",
    },
}

rows = []
for ticker, status in items:
    d = TICKER_DETAIL.get(ticker, {})
    rows.append({
        "Ticker": ticker,
        "Tipo": d.get("tipo", "—"),
        "Status": LABEL[status],
        "AI Entry": d.get("ai", "—"),
        "CVM Docs": d.get("cvm_docs", "—"),
        "CVM Trace": d.get("cvm_trace", "—"),
        "Discrepância": d.get("discrepancy", "—"),
        "Fair Value": d.get("fair_value", "❌"),
        "Valuation Flag": d.get("valuation_available", "—"),
        "Val. Method": d.get("valuation_method", "—"),
        "FQS": d.get("fqs", "—"),
        "Sector": d.get("sector", "—"),
        "Gaps": d.get("gap_count", "—"),
    })

import pandas as pd
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
#  Gaps summary
# ──────────────────────────────────────────────

st.divider()
st.subheader("Consolidado de Gaps")

gap_rows = [
    ["Gap", "Cobertura", "Impacto", "Tickers"],
    ["valuation_method", "0/9 (0%)", "❌ Impossibilita roteamento", "Todos"],
    ["fundamental_quality_score", "0/9 (0%)", "❌ Sem score de robustez", "Todos"],
    ["sector", "0/9 (0%)", "❌ Sem setor — impossibilita roteamento", "Todos"],
    ["company_name", "0/9 (0%)", "❌ Sem nome — impossibilita identificacao", "Todos"],
    ["ai_market_price", "0/9 (0%)", "❌ Sem preco atual no AI", "Todos"],
    ["cvm_docs", "5/9 (56%)", "⚠️ 4 tickers sem demonstracoes", "BPAC11, SANB11, SUZB3, VALE3"],
    ["cvm_trace_discrepancy", "3/9 (33%)", "⚠️ Coleta registrada mas dados nao inseridos", "BPAC11, SANB11, SUZB3"],
    ["fair_value", "4/9 (44%)", "⚠️ 5 tickers sem preco-alvo", "BBDC4, SUZB3, VALE3 + 2 partial"],
    ["ai_entry", "2/9 (22%)", "🔴 Sem entrada — pipeline nao rodou", "BPAC11, SANB11"],
]

gap_df = pd.DataFrame(gap_rows[1:], columns=gap_rows[0])
st.dataframe(gap_df, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
#  Plano de ação
# ──────────────────────────────────────────────

st.divider()
st.subheader("Plano de Acao Priorizado")

action_data = [
    ["Prioridade", "Ação", "Tickers", "Dependência", "Impacto"],
    ["P1 — CRÍTICO", "Reparar discrepancia CVM: trace=6100 mas ri_docs=0", "BPAC11, SANB11, SUZB3", "Nenhuma (S02 itself)", "Restaurar CVM sem re-coletar"],
    ["P1 — CRÍTICO", "Criar AI entry para BPAC11 e SANB11", "BPAC11, SANB11", "Nenhuma", "Tornar tickers visiveis ao pipeline"],
    ["P1 — CRÍTICO", "Executar coleta CVM completa para VALE3 (trace=0)", "VALE3", "Nenhuma (from scratch)", "VALE3 precisa de ingestion completa"],
    ["P2 — ALTO", "Preencher valuation_method para todos", "BBAS3, BBDC4, ITUB4, PETR4, WEGE3, SUZB3, VALE3", "CVM docs OK", "Habilita roteamento de modelo"],
    ["P2 — ALTO", "Calcular fundamental_quality_score", "Todos os 9", "Valuation OK", "Score de robustez dos fundamentos"],
    ["P2 — ALTO", "Preencher sector via CVM ou events", "Todos os 7 com AI entry", "CVM OK", "Roteamento de modelo setorial"],
    ["P2 — ALTO", "Preencher company_name via CVM", "Todos os 9", "CVM OK", "Identificacao legivel"],
    {"P3 — MÉDIO", "Popular ai_market_price (ja existe em cotahist)", "BBAS3, BBDC4, ITUB4, PETR4, WEGE3, SUZB3, VALE3", "AI entry OK", "Calculo de upside"},
    {"P3 — MÉDIO", "Preencher fair_value para BBDC4", "BBDC4", "Valuation OK", "Completar valuation para este ticker"},
]

st.dataframe(pd.DataFrame(action_data[1:], columns=action_data[0]), use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
#  Cross-check: fair values existentes preservados
# ──────────────────────────────────────────────

st.divider()
st.subheader("Cross-Check: Fair Values Preservados")

st.info(
    "Os fair values abaixo existem no banco e **devem ser preservados** — "
    "não devem ser descartados ou recalculados sem evidências novas."
)

fv_rows = [
    ["Ticker", "Fair Value (banco)", "Upside (banco)", "Status", "Ação em S02/S03"],
    ["BBAS3", "R$ 64,84", "0,0%", "PARTIAL", "Preservar — não recalcular"],
    ["ITUB4", "R$ 73,69", "0,0%", "PARTIAL", "Preservar — não recalcular"],
    ["PETR4", "R$ 81,12", "71,2%", "PARTIAL", "Preservar — não recalcular"],
    ["WEGE3", "R$ 40,16", "-10,3%", "PARTIAL", "Preservar — não recalcular"],
    ["BBDC4", "❌ (NULL)", "❌", "NEEDS_MODEL", "Calcular após ingestion"],
    ["SUZB3", "❌ (flag=0)", "❌", "NEEDS_DATA", "Calcular após ingestion"],
    ["VALE3", "❌ (flag=0)", "❌", "NEEDS_DATA", "Calcular após ingestion completa"],
    ["BPAC11", "❌ (sem AI)", "❌", "NEEDS_DATA", "Criar AI entry primeiro"],
    ["SANB11", "❌ (sem AI)", "❌", "NEEDS_DATA", "Criar AI entry primeiro"],
]
st.dataframe(pd.DataFrame(fv_rows[1:], columns=fv_rows[0]), use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────
#  Status Authorization
# ──────────────────────────────────────────────

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("S03 Authorization")
    st.success("✅ **AUTORIZADO** — desde que:")
    st.markdown("""
    - Fair values preservados (BBAS3=64.84, ITUB4=73.69, PETR4=81.12, WEGE3=40.16)
    - CVM ingestion first, valuation second
    - VALE3 treated as ingestion from scratch
    - BPAC11/SANB11 AI entry + CVM repair before valuation
    """)

with col2:
    st.subheader("S04 Scope")
    st.info("📋 **Arquitetura de pipeline de ingestão CVM**")
    st.markdown("""
    - Investigar discrepancy (trace=6100, ri_docs=0)
    - Pipeline de coleta + inserção de ri_documents
    - CVM connector review
    - VALE3 from-scratch ingestion
    """)

st.divider()
st.caption(
    "M014-S02 · valuation_coverage.py · "
    "Baseado em coverage_audit_20260523.csv (S01) · "
    "Nao calcula valuation · Nao altera dados brutos"
)