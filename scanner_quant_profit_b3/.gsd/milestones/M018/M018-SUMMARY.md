# M018 — Summary

**Milestone:** M018 — Controlled Fair Value Calculation, Validation and Preserved Value Review  
**Status:** ✅ FECHADO  
**Data de fechamento:** 2026-05-26  
**Depends on:** M017 ✅ CLOSED (2026-05-26)  
**Próximo:** M019 — Fair Value Promotion and Official Approval

---

## O que foi entregue

M018 executou o primeiro ciclo controlado de cálculo de fair values da plataforma, com ciclo de vida
explícito (`preliminary` → `validated` → `approved`) e proteção total dos valores preservados de M016.

### Slices concluídas

| Slice | Descrição | Status |
|-------|-----------|--------|
| **S01** | Valuation Result Schema and Safe Writer | ✅ Concluída |
| **S02** | Preserved Fair Value Review | ✅ Concluída |
| **S03** | Controlled Calculation Batch for New Tickers | ✅ Concluída |
| **S04** | Sanity Check and Outlier Detection | ✅ Concluída |
| **S05** | Dashboard Integration | ✅ Concluída |

---

## Resultado Final — Valores Preservados (9 tickers)

| Ticker | Fair Value Preservado | Status Final | Observação |
|--------|----------------------:|:------------:|------------|
| ITUB4  | R$ 73,69 | **KEEP** ✅ | Banco — within range |
| PETR4  | R$ 81,12 | **KEEP** ✅ | Commodity — within range |
| WEGE3  | R$ 40,16 | **KEEP** ✅ | Industry — within range |
| BBAS3  | R$ 64,84 | **REVIEW** ⚠️ | Banco — diferença moderada |
| BBDC4  | R$ 34,63 | **REVIEW** ⚠️ | Banco — diferença moderada |
| BRSR6  | R$ 4,66  | **REVIEW** ⚠️ | Banco — diferença moderada |
| ABCB4  | R$ 210,50 | **BLOCKED/REVIEW CRÍTICA** 🔴 | Banco — desvio elevado |
| BPAC11 | R$ 8,46  | **BLOCKED/REVIEW CRÍTICA** 🔴 | Banco — desvio elevado |
| SANB11 | R$ 86,79 | **BLOCKED/REVIEW CRÍTICA** 🔴 | Banco — desvio elevado |

> **Todos os 9 valores preservados permanecem intactos.** Nenhum `approved_fair_value` foi criado.
> Nenhuma sobrescrita ocorreu. `asset_intelligence_snapshots` não foi alterado.

---

## Resultado Final — Valores Preliminares (18 tickers novos)

### Passaram na checagem (sanity_check_passed = 1)

| Ticker | Modelo | Observação |
|--------|--------|------------|
| EGIE3  | UTILITY | ✅ — qualidade alta |
| LREN3  | RETAIL | ✅ — qualidade alta |
| VIVA3  | RETAIL | ✅ — qualidade média |
| RADL3  | INDUSTRY | ✅ — qualidade alta |
| RAIL3  | INDUSTRY | ✅ — qualidade alta |
| RENT3  | INDUSTRY | ✅ — qualidade alta |
| SUZB3  | INDUSTRY | ✅ — qualidade alta |

### Requerem validação (sanity_check_passed = 0 ou flags)

| Ticker | Modelo | Motivo |
|--------|--------|--------|
| PRIO3  | COMMODITY | Abordagem NAV/reservas requerida |
| RECV3  | COMMODITY | qualidade_media — validação necessária |
| SBSP3  | UTILITY | qualidade_media — validação necessária |
| TAEE11 | UTILITY | Requer validação adicional |
| AZZA3  | RETAIL | Upside elevado — validação obrigatória |
| FLRY3  | INDUSTRY | Requer validação |
| HYPE3  | INDUSTRY | Requer validação |
| KLBN11 | INDUSTRY | Validação de unit/shares pendente |
| VAMO3  | INDUSTRY | qualidade_media + upside elevado |

### Baixa confiança / DISTRESSED

| Ticker | Modelo | Status |
|--------|--------|--------|
| MGLU3  | RETAIL | DISTRESSED — FCF negativo, baixa confiança |
| PCAR3  | RETAIL | DISTRESSED — PARTIAL_INPUTS, bloqueio automático |

---

## Invariantes M018 — Cumprimento Integral

| Regra | Verificação |
|-------|-------------|
| RULE-01: Não sobrescrever PRESERVE_EXISTING | ✅ 9/9 intactos |
| RULE-02: preliminary ≠ approved | ✅ 0 approved_fair_value criados |
| RULE-03: 0 writes em asset_intelligence_snapshots | ✅ Confirmado |
| RULE-06/07: Negativo/fora de range bloqueado | ✅ Sanity checks aplicados |
| RULE-08: LLM não calculou | ✅ Todos os números do Financial Engine |
| RULE-09: 0 mocks criados | ✅ Confirmado |
| RULE-11: Opções/OOS/paper/scheduler intocados | ✅ Confirmado |
| RULE-20: Promoção exige sanity_check_passed=True | ✅ Nenhuma promoção automática |

---

## Dashboard

O Valuation Hub foi atualizado (S05) com:
- Seção "PRESERVE_EXISTING" com preservado + recalculado + classification
- Seção "Novos Preliminares" com preliminary_fair_value, confidence, flags, sanity
- Separação visual: "Passou na checagem" / "Requer validação" / "Não aprovado"
- 0 writes via dashboard — read-only confirmado

---

*M018-SUMMARY criado em 2026-05-26.*
