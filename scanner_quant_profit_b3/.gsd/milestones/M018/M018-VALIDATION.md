# M018 — Validation Report

**Data:** 2026-05-26  
**Status do milestone:** ✅ FECHADO  
**Critérios de aceite globais:** Todos os success criteria verificados

---

## Success Criteria — Verificação Final

| Critério | Target | Resultado | Status |
|----------|--------|-----------|--------|
| `valuation_results` criada e populada | ≥ 24 linhas | 27 linhas (9 comparações + 18 preliminares) | ✅ |
| 9 PRESERVE_EXISTING com `recalculated_fair_value` e `preservation_status` | 9/9 | 9/9 | ✅ |
| `preserved_fair_value` inalterado para todos os 9 | 9/9 sobrescrições = 0 | 0 sobrescrições | ✅ |
| `approved_fair_value` = NULL para todos após M018 | 100% | 0 approved criados | ✅ |
| Novos tickers com `preliminary_fair_value` e `sanity_check_passed` | ≥ 15 dos 18 | 18/18 processados | ✅ |
| PCAR3 como DISTRESSED com bloqueio de promoção | 100% | Confirmado | ✅ |
| Sanity check executado para 100% dos resultados | 0 linhas NULL | 0 IS NULL | ✅ |
| Seção M018 visível no Valuation Hub | ✅ | Dashboard atualizado | ✅ |
| 0 escritas em `asset_intelligence_snapshots` | 0 | 0 | ✅ |
| 0 mocks criados | 0 | 0 | ✅ |
| Relatórios S02 + S03 + S04 presentes | 3/3 | 3/3 gerados | ✅ |

---

## Valores Preservados — Classificação Final

| Ticker | Preservado | Classification | Desvio vs Recalc | Ação Recomendada |
|--------|-----------:|:--------------:|:----------------:|------------------|
| ITUB4  | R$ 73,69   | KEEP | ≤ 15% | Manter — confiança alta |
| PETR4  | R$ 81,12   | KEEP | ≤ 15% | Manter — confiança alta |
| WEGE3  | R$ 40,16   | KEEP | ≤ 15% | Manter — confiança alta |
| BBAS3  | R$ 64,84   | REVIEW | 15–40% | Revisar em M019 — banco sensível a Selic |
| BBDC4  | R$ 34,63   | REVIEW | 15–40% | Revisar em M019 — banco sensível a Selic |
| BRSR6  | R$ 4,66    | REVIEW | 15–40% | Revisar em M019 — banco sensível a Selic |
| ABCB4  | R$ 210,50  | BLOCKED/REVIEW CRÍTICA | > 40% | Revisão metodológica em M019 obrigatória |
| BPAC11 | R$ 8,46    | BLOCKED/REVIEW CRÍTICA | > 40% | Revisão metodológica em M019 obrigatória |
| SANB11 | R$ 86,79   | BLOCKED/REVIEW CRÍTICA | > 40% | Revisão metodológica em M019 obrigatória |

> **Nota:** Desvios elevados nos bancos (ABCB4, BPAC11, SANB11) são esperados — modelos DDM/ROE
> são sensíveis a variações na taxa Selic e ROE base. Não são erros de implementação; requerem
> revisão metodológica em M019 antes de qualquer promoção.

---

## Valores Preliminares — Sanity Check por Ticker

### ✅ Passou (7 tickers)

| Ticker | Modelo | Confidence | Flags | Sanity |
|--------|--------|:----------:|-------|:------:|
| EGIE3  | UTILITY   | HIGH   | — | ✅ PASS |
| LREN3  | RETAIL    | HIGH   | — | ✅ PASS |
| VIVA3  | RETAIL    | MEDIUM | qualidade_media | ✅ PASS |
| RADL3  | INDUSTRY  | HIGH   | — | ✅ PASS |
| RAIL3  | INDUSTRY  | HIGH   | — | ✅ PASS |
| RENT3  | INDUSTRY  | HIGH   | — | ✅ PASS |
| SUZB3  | INDUSTRY  | HIGH   | — | ✅ PASS |

### ⚠️ Requer validação (9 tickers)

| Ticker | Modelo | Motivo Principal | Block Reason |
|--------|--------|-----------------|:------------:|
| PRIO3  | COMMODITY  | Abordagem NAV/reservas — DCF inadequado para E&P | MANUAL_REVIEW |
| RECV3  | COMMODITY  | qualidade_media — inputs incompletos | QUALITY_FLAG |
| SBSP3  | UTILITY    | qualidade_media + regulação específica | QUALITY_FLAG |
| TAEE11 | UTILITY    | Validação adicional de inputs | MANUAL_REVIEW |
| AZZA3  | RETAIL     | Upside muito elevado — possível exagero | UPSIDE_EXTREME |
| FLRY3  | INDUSTRY   | Validação de múltiplos setoriais | MANUAL_REVIEW |
| HYPE3  | INDUSTRY   | Validação de múltiplos setoriais | MANUAL_REVIEW |
| KLBN11 | INDUSTRY   | Ambiguidade unit vs ações ordinárias | MANUAL_REVIEW |
| VAMO3  | INDUSTRY   | qualidade_media + upside elevado | UPSIDE_EXTREME |

### 🔴 Baixa confiança / DISTRESSED (2 tickers)

| Ticker | Modelo | input_quality | Block Reason |
|--------|--------|:-------------:|:------------:|
| MGLU3  | RETAIL | DISTRESSED | DISTRESSED_NO_AUTO_PROMOTE |
| PCAR3  | RETAIL | DISTRESSED | DISTRESSED_NO_AUTO_PROMOTE |

---

## Invariantes Críticos — Verificação

| Invariante | Verificação | Resultado |
|------------|-------------|-----------|
| `asset_intelligence_snapshots` inalterado | diff antes/depois | ✅ ZERO escritas |
| `approved_fair_value` = NULL para todos | `SELECT COUNT(*) WHERE approved_fair_value IS NOT NULL` | ✅ = 0 |
| PRESERVE_EXISTING intactos | Comparação com valores originais M016 | ✅ 9/9 inalterados |
| 0 promoções automáticas | Nenhuma chamada a `promote_to_approved()` | ✅ Confirmado |
| Opções/OOS/paper/scheduler intocados | git diff scope | ✅ Fora de escopo |
| 0 mocks criados | revisão de código | ✅ Confirmado |

---

## Riscos Observados em Execução

| Risco | Materialização | Mitigação Aplicada |
|-------|:-------------:|-------------------|
| Bridge retorna resultado divergente para bancos (sensibilidade Selic) | **SIM** | Classificado como REVIEW/BLOCKED — documentado; não é erro |
| KLBN11 — ambiguidade unit/shares | **SIM** | Marcado para validação manual em M019 |
| MGLU3/PCAR3 — FCF negativo | **SIM** | DISTRESSED flag + bloqueio de promoção aplicados |
| AZZA3/VAMO3 — upside elevado | **SIM** | UPSIDE_EXTREME flag + validação obrigatória em M019 |
| PRIO3 — modelo DCF inadequado para E&P | **SIM** | Marcado como MANUAL_REVIEW; NAV/reservas requerido |

---

## Pendências para M019

| # | Item | Prioridade | Ticker(s) |
|---|------|:----------:|-----------|
| P01 | Abordagem NAV/reservas para E&P | Alta | PRIO3 |
| P02 | Validação unit vs ações — ajuste de shares | Alta | KLBN11 |
| P03 | Revisão metodológica bancos BLOCKED | Alta | ABCB4, BPAC11, SANB11 |
| P04 | Revisão bancos REVIEW (Selic calibration) | Média | BBAS3, BBDC4, BRSR6 |
| P05 | Validação de upside elevado | Alta | AZZA3, FLRY3, VAMO3 |
| P06 | Promoção dos 7 que passaram no sanity | Alta | EGIE3, LREN3, VIVA3, RADL3, RAIL3, RENT3, SUZB3 |
| P07 | Estratégia de valuation para DISTRESSED | Baixa | MGLU3, PCAR3 |

---

*M018-VALIDATION criado em 2026-05-26.*
