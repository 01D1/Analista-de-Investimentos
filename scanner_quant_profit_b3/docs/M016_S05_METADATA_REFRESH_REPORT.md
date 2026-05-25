# M016-S05 — Metadata Refresh e Coverage Promotion
**Data:** 2026-05-25  
**Status:** ✅ CONCLUÍDA  
**Milestone:** M016 — Sector Normalization and Valuation Model Engine  
**Slice:** S05 (última slice do milestone)  
**Dependências:** S01 ✅ · S02 ✅ · S03 ✅ · S04 ✅

---

## 1. Objetivo

Atualizar metadados de coverage/valuation readiness após a implementação dos modelos
S01–S04, sem calcular valuation novo e sem promover ticker sem dados financeiros reais.

Confirmar:
- Fair values preservados vs. sobrescritos
- Tickers com modelo disponível mas sem inputs financeiros estruturados
- Tickers ainda bloqueados por dados ausentes
- Tickers fora do valuation principal (LEGACY/NEEDS_RI_DOCS/NEEDS_DATA)

---

## 2. Diagnose Batch — Resultados por Modelo

### 2.1 BANK MODEL — 7 tickers

**Implementação:** `src/valuation/models/bank_model.py`  
**Metodologia:** P/BV justificado (primário) + DDM/Gordon (secundário) + Relativos (fallback)

| Ticker | Status Final | Fair Value | Source | Market Price | Blocked |
|--------|-------------|-----------|--------|-------------|---------|
| ABCB4  | PRESERVE_EXISTING | R$210.50 | Excel Pipeline | N/A | ❌ |
| BBAS3  | PRESERVE_EXISTING | R$64.84  | PRESERVED_DICT | N/A | ❌ |
| BBDC4  | PRESERVE_EXISTING | R$34.63  | Excel Pipeline | N/A | ❌ |
| BPAC11 | PRESERVE_EXISTING | R$8.46   | Excel Pipeline | N/A | ❌ |
| BRSR6  | PRESERVE_EXISTING | R$4.66   | Excel Pipeline | N/A | ❌ |
| ITUB4  | PRESERVE_EXISTING | R$73.69  | PRESERVED_DICT | N/A | ❌ |
| SANB11 | PRESERVE_EXISTING | R$86.79  | Excel Pipeline | N/A | ❌ |

**Resultado BANK:** 7/7 PRESERVE_EXISTING · 0 NEEDS_FINANCIALS · 0 novos fair_values calculados

---

### 2.2 COMMODITY MODEL — 4 tickers

**Implementação:** `src/valuation/models/commodity_model.py`  
**Metodologia:** DCF/FCFF (primário) + EV/EBITDA (secundário)

| Ticker | Status Final | Fair Value | RI Docs | Bloqueio |
|--------|-------------|-----------|---------|---------|
| PETR4  | PRESERVE_EXISTING | R$81.12 | 131 | ❌ Não bloqueado |
| PRIO3  | NEEDS_FINANCIALS  | —       | 109 | ✅ D-COMM-03: net_debt ausente |
| RECV3  | NEEDS_FINANCIALS  | —       | 126 | ✅ D-COMM-03: net_debt ausente |
| VALE3  | NEEDS_DATA        | —       | 0   | ✅ ri_docs=0 — bloqueio absoluto |

**Resultado COMMODITY:** 1/4 PRESERVE · 2/4 NEEDS_FINANCIALS · 1/4 NEEDS_DATA · 0 novos fair_values

---

### 2.3 UTILITY MODEL — 3 tickers

**Implementação:** `src/valuation/models/utility_model.py`  
**Metodologia:** RAB-DCF (primário) + DCF/FCFF (secundário) + EV/EBITDA (terciário)

| Ticker | Status Final | Fair Value | RI Docs | Bloqueio |
|--------|-------------|-----------|---------|---------|
| EGIE3  | NEEDS_FINANCIALS | — | 129 | ✅ U-UTIL-03: net_debt ausente |
| SBSP3  | NEEDS_FINANCIALS | — | 123 | ✅ U-UTIL-03: net_debt ausente |
| TAEE11 | NEEDS_FINANCIALS | — | 137 | ✅ U-UTIL-03: net_debt ausente |

**Resultado UTILITY:** 0/3 PRESERVE · 3/3 NEEDS_FINANCIALS · 0 novos fair_values

---

### 2.4 RETAIL MODEL — 5 tickers

**Implementação:** `src/valuation/models/retail_model.py`  
**Metodologia:** DCF/FCFF (primário) + EV/EBITDA (secundário) + flag DISTRESSED

| Ticker | Status Final | Fair Value | RI Docs | Bloqueio |
|--------|-------------|-----------|---------|---------|
| AZZA3  | NEEDS_FINANCIALS | — | 131 | ✅ R-RETAIL-03: net_debt ausente |
| LREN3  | NEEDS_FINANCIALS | — | 130 | ✅ R-RETAIL-03: net_debt ausente |
| MGLU3  | NEEDS_FINANCIALS | — | 129 | ✅ R-RETAIL-03: net_debt ausente |
| PCAR3  | NEEDS_FINANCIALS | — | 126 | ✅ R-RETAIL-03: net_debt ausente |
| VIVA3  | NEEDS_FINANCIALS | — | 132 | ✅ R-RETAIL-03: net_debt ausente |

**Resultado RETAIL:** 0/5 PRESERVE · 5/5 NEEDS_FINANCIALS · 0 novos fair_values

---

### 2.5 INDUSTRY MODEL — 10 tickers (incluindo TECH/FALLBACK)

**Implementação:** `src/valuation/models/industry_model.py`  
**Metodologia:** DCF/FCFF (primário) + EV/EBITDA (secundário)

| Ticker | Status Final | Fair Value | RI Docs | Bloqueio / Nota |
|--------|-------------|-----------|---------|----------------|
| FLRY3  | NEEDS_FINANCIALS | — | 128 | ✅ I-IND-03: net_debt ausente |
| HYPE3  | NEEDS_FINANCIALS | — | 132 | ✅ I-IND-03: net_debt ausente |
| KLBN11 | NEEDS_FINANCIALS | — | 129 | ✅ I-IND-03: net_debt ausente |
| RADL3  | NEEDS_FINANCIALS | — | 129 | ✅ I-IND-03: net_debt ausente |
| RAIL3  | NEEDS_FINANCIALS | — | 135 | ✅ I-IND-03: net_debt ausente |
| RENT3  | NEEDS_FINANCIALS | — | 129 | ✅ I-IND-03: net_debt ausente |
| SUZB3  | NEEDS_FINANCIALS | — | 131 | ✅ I-IND-03: net_debt ausente |
| VAMO3  | NEEDS_FINANCIALS | — | 17  | ✅ I-IND-03: net_debt ausente (low RI) |
| WEGE3  | PRESERVE_EXISTING | R$40.16 | 124 | ❌ Não bloqueado |
| VIVT3  | TECH_FALLBACK  | — | 128 | ✅ Sem modelo próprio (TECH_FALLBACK) |

**Resultado INDUSTRY:** 1/10 PRESERVE · 8/10 NEEDS_FINANCIALS · 1/10 TECH_FALLBACK · 0 novos fair_values

---

## 3. Matriz Final de Coverage — Todos os Tickers M016

### 3.1 Tickers com Fair Value Preservado (9 tickers)

| Ticker | Fair Value | Método Modelo | Grupo |
|--------|-----------|-------------|-------|
| ABCB4  | R$210.50 | COSIF/DDM (P/BV) | BANK |
| BBAS3  | R$64.84  | COSIF/DDM (P/BV) | BANK |
| BBDC4  | R$34.63  | COSIF/DDM (P/BV) | BANK |
| BPAC11 | R$8.46   | COSIF/DDM (P/BV) | BANK |
| BRSR6  | R$4.66   | COSIF/DDM (P/BV) | BANK |
| ITUB4  | R$73.69  | COSIF/DDM (P/BV) | BANK |
| SANB11 | R$86.79  | COSIF/DDM (P/BV) | BANK |
| PETR4  | R$81.12  | DCF/FCFF         | COMMODITY |
| WEGE3  | R$40.16  | DCF/FCFF         | INDUSTRY |

> Nenhum desses valores foi sobrescrito. Todos preservados com `force_recalc=False` (default).

---

### 3.2 Tickers com Modelo Disponível mas sem Inputs Estruturados (18 tickers)

Status: **MODEL_AVAILABLE_NO_INPUTS** — Modelo implementado, RI docs presentes,
mas EBITDA/FCF/net_debt/shares não parseados estruturadamente no banco.

| Ticker | Grupo | Modelo | RI Docs | Bloqueio Principal |
|--------|-------|--------|---------|-------------------|
| PRIO3  | COMMODITY | commodity_model.py | 109 | net_debt ausente |
| RECV3  | COMMODITY | commodity_model.py | 126 | net_debt ausente |
| EGIE3  | UTILITY   | utility_model.py   | 129 | net_debt + RAB ausentes |
| SBSP3  | UTILITY   | utility_model.py   | 123 | net_debt + RAB ausentes |
| TAEE11 | UTILITY   | utility_model.py   | 137 | net_debt + RAB ausentes |
| AZZA3  | RETAIL    | retail_model.py    | 131 | net_debt ausente |
| LREN3  | RETAIL    | retail_model.py    | 130 | net_debt ausente |
| MGLU3  | RETAIL    | retail_model.py    | 129 | net_debt ausente |
| PCAR3  | RETAIL    | retail_model.py    | 126 | net_debt ausente |
| VIVA3  | RETAIL    | retail_model.py    | 132 | net_debt ausente |
| FLRY3  | INDUSTRY  | industry_model.py  | 128 | net_debt ausente |
| HYPE3  | INDUSTRY  | industry_model.py  | 132 | net_debt ausente |
| KLBN11 | INDUSTRY  | industry_model.py  | 129 | net_debt ausente |
| RADL3  | INDUSTRY  | industry_model.py  | 129 | net_debt ausente |
| RAIL3  | INDUSTRY  | industry_model.py  | 135 | net_debt ausente |
| RENT3  | INDUSTRY  | industry_model.py  | 129 | net_debt ausente |
| SUZB3  | INDUSTRY  | industry_model.py  | 131 | net_debt ausente |
| VAMO3  | INDUSTRY  | industry_model.py  | 17  | net_debt ausente |

> Ação necessária: parsing estruturado de DFP/ITR para extrair EBITDA, FCF, net_debt, shares.
> Quando esses dados forem injetados, o modelo calcula fair_value sem bloqueio.

---

### 3.3 Tickers Bloqueados — Fora do Valuation Principal

| Ticker | Status | Motivo | RI Docs | Ação Necessária |
|--------|--------|--------|---------|----------------|
| VALE3  | NEEDS_DATA    | ri_docs=0 — bloqueio absoluto | 0 | CVM ingestion (SXX) |
| VIVT3  | TECH_FALLBACK | Sem modelo próprio em M016-S04; roteado via INDUSTRY | 128 | N/A (modelo DCF já aplicável) |
| PETZ3  | LEGACY_TICKER | Extinto por fusão 2026-01-02 — permanentemente bloqueado | — | Nenhuma — permanente |
| AUAU3  | NEEDS_RI_DOCS | Successor de PETZ3; sem RI ainda (prazo CVM) | ~0 | Aguardar CVM ingestion |
| NTCO3  | NEEDS_RI_DOCS | Sem RI docs no banco | ~0 | CVM ingestion |

> Nota VIVT3: O modelo industry_model.py já trata VIVT3 via TECH_FALLBACK com DCF/FCFF.
> O bloqueio é por falta de inputs (net_debt/FCF), não por ausência de modelo.
> Quando financials estiverem disponíveis, VIVT3 calcula via industry_model → DCF.

---

### 3.4 Tickers Fora do Universo M016 (tipo bank, sem RI)

| Ticker | Tipo (yaml) | Setor Canônico | Status |
|--------|------------|---------------|--------|
| BMGB4  | bank | BANK | NEEDS_RI_DOCS |
| BPAN4  | bank | BANK | NEEDS_RI_DOCS |
| PINE4  | bank | BANK | NEEDS_RI_DOCS |

> Estes tickers têm tipo mapeado no SectorNormalizer mas não fazem parte do universo de 28 READY.
> Não entram no diagnose batch de M016.

---

## 4. Mapa de Modelos Disponíveis

| Modelo | Arquivo | Tickers Cobertos | Estado |
|--------|---------|-----------------|--------|
| bank_model | `src/valuation/models/bank_model.py` | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11 | ✅ ATIVO |
| commodity_model | `src/valuation/models/commodity_model.py` | PETR4, PRIO3, RECV3, VALE3 | ✅ ATIVO |
| utility_model | `src/valuation/models/utility_model.py` | EGIE3, SBSP3, TAEE11 | ✅ ATIVO |
| retail_model | `src/valuation/models/retail_model.py` | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 | ✅ ATIVO |
| industry_model | `src/valuation/models/industry_model.py` | FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3, WEGE3, VIVT3 | ✅ ATIVO |
| sector_normalizer | `src/valuation/sector_normalizer.py` | Todos os tickers | ✅ ATIVO |

---

## 5. Testes Executados

### Suítes de Teste M016

| Arquivo de Teste | Testes | Resultado | Tempo |
|------------------|--------|-----------|-------|
| `tests/test_sector_normalizer.py` | 134 | ✅ 134 passed | — |
| `tests/test_bank_model.py` | 91 | ✅ 91 passed | — |
| `tests/test_commodity_model.py` | 71 | ✅ 71 passed | — |
| `tests/test_utility_model.py` | 59 | ✅ 59 passed | — |
| `tests/test_retail_model.py` | 59 | ✅ 59 passed | — |
| `tests/test_industry_model.py` | 63 | ✅ 63 passed | — |
| `tests/test_router.py` | 27 | ✅ 27 passed | — |
| `tests/test_valuation_stores.py` | 30 | ✅ 30 passed | — |
| **TOTAL** | **514** | **✅ 514/514** | **1.78s** |

> Todos os 514 testes passaram. Nenhum teste falhou, nenhum skipado.

---

## 6. Invariantes M016 Verificados

| Regra | Verificação |
|-------|------------|
| RULE-01: Não sobrescrever fair_values sem force_recalc | ✅ 9 valores preservados, 0 sobrescritos |
| RULE-02: Não calcular para NEEDS_SECTOR/NEEDS_RI_DOCS/LEGACY | ✅ PETZ3/AUAU3/NTCO3/VALE3 bloqueados |
| RULE-03: PETZ3 = LEGACY_TICKER permanente | ✅ Permanece LEGACY_TICKER |
| RULE-04: AUAU3 só entra após ri_docs > 0 | ✅ Fora do valuation |
| RULE-05: VALE3 só entra após SXX | ✅ NEEDS_DATA (ri_docs=0) |
| RULE-06: terminal_growth < WACC hard-block | ✅ Todos os modelos implementam D-COMM-02/I-IND-02 |
| RULE-07: fair_value só gerado com inputs rastreáveis | ✅ 0 fair_values calculados sem dados |
| RULE-08: input_hash populado em todo ValuationResult | ✅ Implementado em todos os modelos |
| RULE-09: 0 mocks criados | ✅ Confirmado — todos os resultados são de dados reais ou bloqueados |
| RULE-10: Não alterar opções/OOS/paper/scheduler | ✅ Não tocado |

---

## 7. Consolidação de Status por Ticker

### Status Final Completo — 28 Tickers READY + Fora de Escopo

| Ticker | Grupo | Status | Fair Value | RI Docs | Modelo Disponível |
|--------|-------|--------|-----------|---------|------------------|
| ABCB4  | BANK | PRESERVE_EXISTING | R$210.50 | >100 | ✅ bank_model |
| BBAS3  | BANK | PRESERVE_EXISTING | R$64.84 | >100 | ✅ bank_model |
| BBDC4  | BANK | PRESERVE_EXISTING | R$34.63 | >100 | ✅ bank_model |
| BPAC11 | BANK | PRESERVE_EXISTING | R$8.46 | >100 | ✅ bank_model |
| BRSR6  | BANK | PRESERVE_EXISTING | R$4.66 | >100 | ✅ bank_model |
| ITUB4  | BANK | PRESERVE_EXISTING | R$73.69 | >100 | ✅ bank_model |
| SANB11 | BANK | PRESERVE_EXISTING | R$86.79 | >100 | ✅ bank_model |
| PETR4  | COMMODITY | PRESERVE_EXISTING | R$81.12 | 131 | ✅ commodity_model |
| PRIO3  | COMMODITY | NEEDS_FINANCIALS | — | 109 | ✅ commodity_model |
| RECV3  | COMMODITY | NEEDS_FINANCIALS | — | 126 | ✅ commodity_model |
| EGIE3  | UTILITY | NEEDS_FINANCIALS | — | 129 | ✅ utility_model |
| SBSP3  | UTILITY | NEEDS_FINANCIALS | — | 123 | ✅ utility_model |
| TAEE11 | UTILITY | NEEDS_FINANCIALS | — | 137 | ✅ utility_model |
| AZZA3  | RETAIL | NEEDS_FINANCIALS | — | 131 | ✅ retail_model |
| LREN3  | RETAIL | NEEDS_FINANCIALS | — | 130 | ✅ retail_model |
| MGLU3  | RETAIL | NEEDS_FINANCIALS | — | 129 | ✅ retail_model |
| PCAR3  | RETAIL | NEEDS_FINANCIALS | — | 126 | ✅ retail_model |
| VIVA3  | RETAIL | NEEDS_FINANCIALS | — | 132 | ✅ retail_model |
| FLRY3  | INDUSTRY | NEEDS_FINANCIALS | — | 128 | ✅ industry_model |
| HYPE3  | INDUSTRY | NEEDS_FINANCIALS | — | 132 | ✅ industry_model |
| KLBN11 | INDUSTRY | NEEDS_FINANCIALS | — | 129 | ✅ industry_model |
| RADL3  | INDUSTRY | NEEDS_FINANCIALS | — | 129 | ✅ industry_model |
| RAIL3  | INDUSTRY | NEEDS_FINANCIALS | — | 135 | ✅ industry_model |
| RENT3  | INDUSTRY | NEEDS_FINANCIALS | — | 129 | ✅ industry_model |
| SUZB3  | INDUSTRY | NEEDS_FINANCIALS | — | 131 | ✅ industry_model |
| VAMO3  | INDUSTRY | NEEDS_FINANCIALS | — | 17 | ✅ industry_model |
| WEGE3  | INDUSTRY | PRESERVE_EXISTING | R$40.16 | 124 | ✅ industry_model |
| VIVT3  | TECH_FALLBACK | TECH_FALLBACK | — | 128 | ✅ industry_model (DCF) |
| VALE3  | COMMODITY | NEEDS_DATA | — | 0 | ✅ commodity_model (bloqueado) |
| PETZ3  | — | LEGACY_TICKER | — | — | ✗ bloqueado permanente |
| AUAU3  | — | NEEDS_RI_DOCS | — | ~0 | aguardando CVM |
| NTCO3  | — | NEEDS_RI_DOCS | — | ~0 | aguardando CVM |

---

## 8. Análise: Por que NEEDS_FINANCIALS é o estado correto

Os 18 tickers com status NEEDS_FINANCIALS têm RI docs no banco (CVM), mas os dados
financeiros estruturados (EBITDA, FCF, net_debt, shares_outstanding) **não foram
extraídos/parseados** do conteúdo desses documentos para o formato tabular esperado
pelos modelos.

**O que existe:**
- Documentos RI (ITR/DFP/IPE) no banco SQLite (`ri_documents`)
- Modelo de valuation implementado e testado
- SectorNormalizer roteando corretamente

**O que falta:**
- Parser de DFP/ITR extraindo campos: EBITDA, FCFF, net_debt, shares_outstanding
- Tabela `b3_financials` ou equivalente com dados estruturados por ticker/período
- Ingestão via COSIF (para bancos sem Excel pipeline)

**Próximo milestone (pós-M016):**
Implementar parsing estruturado de ITR/DFP → alimentar modelos de valuation
→ promover todos os 18 NEEDS_FINANCIALS para VALUATION_READY automaticamente.

---

## 9. Próximos Passos Recomendados

| Prioridade | Ação | Benefício |
|-----------|------|-----------|
| P1 | Parsing estruturado DFP/ITR: EBITDA, FCFF, net_debt, shares | 18 tickers → VALUATION_READY |
| P2 | CVM ingestion VALE3 (SXX) | VALE3 → NEEDS_FINANCIALS → elegível |
| P3 | CVM ingestion NTCO3, AUAU3 | 2 tickers → NEEDS_FINANCIALS |
| P4 | COSIF parser para BMGB4/BPAN4/PINE4 | 3 bancos adicionais |
| P5 | Modelo próprio TECH (ARPU/EBITDA) | VIVT3 com confiança > TECH_FALLBACK |

---

## 10. Autorização para Fechar M016

### Critérios de Sucesso M016

| Critério | Target | Resultado | Status |
|----------|--------|-----------|--------|
| SectorNormalizer: 28/28 tickers com chave canônica correta | 100% | 28/28 ✅ | ✅ |
| Tickers com fair_value calculado ou preservado | ≥ 15/28 | **9/28** preservados | ⚠️ Abaixo do target |
| Tickers READY após S05 | ≥ 10 | 9 PRESERVE_EXISTING | ⚠️ Abaixo do target |
| Nenhum fair_value anterior sobrescrito | 0 | 0 sobrescrições | ✅ |
| PETZ3 permanece LEGACY_TICKER | 100% | ✅ | ✅ |
| VALE3/NTCO3/AUAU3 fora do valuation | 100% | ✅ | ✅ |
| Validação terminal_growth < WACC | 0 explosões | 0 | ✅ |
| input_hash em todos os resultados | 100% | ✅ | ✅ |
| 0 mocks criados | 0 | 0 | ✅ |

### Análise do Gap vs. Target

O target original previa **≥ 15 tickers com fair_value calculado** — assumindo que
parsing de DFP/ITR estaria disponível para alimentar os modelos. Contudo, os dados
financeiros estruturados (EBITDA, FCF, net_debt) ainda não foram parseados dos RI docs.

**Por que isso é o estado correto:**

1. Os modelos foram implementados **corretamente** — calculam quando dados existem
2. O diagnose batch **detectou corretamente** a ausência de inputs estruturados
3. Nenhum valor foi calculado por falta de dados — o que é **o comportamento esperado**
4. Os 9 valores preservados são **reais** (Excel pipeline ou dicionaries auditáveis)

**Recomendação:** M016 pode ser fechado com status PARTIAL-SUCCESS:
- S01, S02, S03, S04, S05: todos concluídos ✅
- Infra de valuation: 100% funcional ✅
- Fair values calculados: 9/28 (preservados) — limitação por dados, não por modelo ✅
- Gap residual: parsing DFP/ITR → novo milestone M017 (ou extensão via SXX)

---

*Relatório gerado em 2026-05-25 · M016-S05-METADATA-REFRESH*  
*Baseado em: diagnose_bank_tickers() · diagnose_commodity_tickers() · diagnose_utility_tickers() · diagnose_retail_tickers() · diagnose_industry_tickers()*  
*Testes: 514/514 passed · Duração: 1.78s*
