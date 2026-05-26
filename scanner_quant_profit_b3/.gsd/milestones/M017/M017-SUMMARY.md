# M017 — Structured DFP/ITR Financial Statements Parser

**Data:** 2026-05-26 | **Milestone:** M017 | **Status:** ✅ FECHADO

## One-liner

Infraestrutura completa de dados financeiros implementada: schema `valuation_financial_inputs`
+ Metric Extraction Engine (21 métricas, 47.621 registros, 88 tickers) + bridge que hidrata
dataclasses dos modelos M016 — 18/18 tickers NEEDS_FINANCIALS produzem `fair_value` em
dry-run (write=False); 401/401 testes passando; 0 fair values calculados; M018 autorizado.

---

## Resumo por Slice

| Slice | Título | Status | Key Deliverable |
|-------|--------|:------:|-----------------|
| S01 | Financial Inputs Schema | ✅ | `valuation_financial_inputs` table + `FinancialInputsStore` + 29 testes; schema com `input_hash` e `source_priority` |
| S02.5 | CVM Dataset Expansion | ✅ | Download universo amplo (~88 tickers); descoberta cloud-only files + DRE/DFC ausentes; relatório de cobertura |
| S02.6 | CVM Code Correction | ✅ | Purge EQTL3/VAMO3 (9.407 linhas contaminadas) + reingestão CD_CVM corretos; 1.150.497 linhas válidas em `cvm_statements` |
| S03 | Metric Extraction Engine | ✅ | `metric_extractor.py`; 21 métricas (16 diretas + 5 derivadas); 47.603 registros; 88/89 tickers; fix `KeyError: CD_CVM` |
| S04 | Shares Outstanding | ✅ | `shares_outstanding` via yfinance para 18 tickers; 47.621 total; 17/18 READY_TO_CALCULATE; PCAR3 PARTIAL_INPUTS |
| S05 | Financial Inputs Bridge | ✅ | `financial_inputs_bridge.py`; 18/18 tickers → dry-run fair_value (write=False); `M017_S05_DRY_RUN_MATRIX.csv` |

---

## Decisões Registradas (M017)

| ID | Decisão | Status |
|----|---------|:------:|
| D111 | Two-track approach: Track A (Excel, 9 tickers) + Track B (CVM CSV, 17) — Track B autoritário | ✅ |
| D112 | `valuation_financial_inputs` = tabela canônica para inputs financeiros estruturados | ✅ |
| D113 | VAMO3 = MANUAL_REVIEW — sem fonte disponível; não criar mock; não bloquear M017 | ✅ |
| D114 | `dfp_parser.py` de 12_PYTHON auditado em S02 antes de qualquer adaptação | ✅ |
| D115 | `shares_outstanding` sem fonte CVM CSV → fallback yfinance (sharesOutstanding) | ✅ |
| D116 | `ri_documents.extracted_text` = empty (0/3.251) — não é fonte viável | ✅ |
| D117 | M017 não calcula fair_value — apenas popula `valuation_financial_inputs`; M018 calcula | ✅ |
| D118 | `input_hash` obrigatório em `valuation_financial_inputs` como gate de re-extração | ✅ |
| D119 | Código de conta CVM (numérico) = identificador primário; nome literal = fallback | ✅ |
| D120 | Track A preenche apenas campos None do Track B — não sobrepõe CVM | ✅ |
| D121 | S02.5 inserida antes de S03: S02 revelou arquivos cloud-only — resolver dataset primeiro | ✅ |
| D122 | Dataset amplo (~88 tickers); 18 NEEDS_FINANCIALS = prioridade, não limite estrutural | ✅ |
| D123 | AUAU3 (CNPJ nulo) e PETZ3 (LEGACY_TICKER) excluídos explicitamente de S02.5 | ✅ |

---

## Arquivos Criados / Alterados

| Slice | Arquivo | Ação | Descrição |
|-------|---------|------|-----------|
| S01 | `src/ingestion/valuation_financial_inputs.py` | CRIADO | Schema SQLite + DDL |
| S01 | `src/ingestion/financial_inputs_store.py` | CRIADO | `FinancialInputsStore` CRUD |
| S01 | `tests/test_financial_inputs_store.py` | CRIADO | 29 testes |
| S02.6 | `12_PYTHON/run_reingest_from_filtered.py` | CRIADO | CLI reingestão pós-purge |
| S02.6 | `12_PYTHON/run_cvm_purge_reingest.py` | CRIADO | Script purge + reingestão |
| S02.6 | `12_PYTHON/docs/M017_S02.6_CVM_CODE_CORRECTION_REPORT.md` | CRIADO | Relatório de correção |
| S03 | `src/ingestion/metric_extractor.py` | CRIADO | Engine extração 21 métricas |
| S03 | `12_PYTHON/run_extract_metrics.py` | CRIADO | CLI runner (canary/batch) |
| S03 | `src/ingestion/cvm_downloader.py` | ALTERADO | Fix `KeyError: CD_CVM` |
| S04 | `src/ingestion/metric_extractor.py` | ALTERADO | shares via yfinance |
| S04 | `12_PYTHON/docs/M017_S04_MODEL_READINESS_REPORT.md` | CRIADO | Relatório prontidão |
| S04 | `12_PYTHON/docs/M017_S04_COVERAGE_MATRIX.csv` | CRIADO | Matriz 18 × 15 métricas |
| S05 | `src/valuation/financial_inputs_bridge.py` | CRIADO | Bridge store → dataclasses |
| S05 | `tests/test_financial_inputs_bridge.py` | CRIADO | Testes da bridge |
| S05 | `src/valuation/__init__.py` | ALTERADO | Exports bridge |
| S05 | `12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv` | CRIADO | Matriz dry-run 18 tickers |

---

## Estado do Banco Post-M017

| Tabela | Registros | Δ vs Pre-M017 | Observação |
|--------|----------:|:-------------:|------------|
| `valuation_financial_inputs` | **47.621** | +47.621 | 21 métricas × 88 tickers + shares |
| `cvm_statements` | **1.150.497** | net +17.888 | Purge 9.407 + reingestão EQTL3/VAMO3 corretos |
| `asset_intelligence_snapshots` | inalterado | 0 | M017 não toca snapshots |

---

## Estado do Universo Post-M017

| Status | Count | Tickers |
|--------|------:|---------|
| PRESERVE_EXISTING (fair_value auditável) | 9 | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11, PETR4, WEGE3 |
| READY_TO_CALCULATE (inputs completos) | 17 | PRIO3, RECV3, EGIE3, SBSP3, TAEE11, AZZA3, LREN3, MGLU3, VIVA3, FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3 |
| PARTIAL_INPUTS (≥1 campo crítico ausente) | 1 | PCAR3 (DISTRESSED — EV/EBITDA only) |
| TECH_FALLBACK | 1 | VIVT3 |
| NEEDS_DATA (ri_docs=0) | 1 | VALE3 |
| NEEDS_RI_DOCS | 2 | AUAU3, NTCO3 |
| LEGACY_TICKER (permanente) | 1 | PETZ3 |

---

## Flags de Qualidade (18 tickers)

| Ticker | Flag | Detalhe |
|--------|------|---------|
| MGLU3 | FCF_REVIEW | OCF=15.7B vs EBITDA=3.2B (4.8× — anomalous) |
| PCAR3 | DISTRESSED | EBIT=-169M, NI=-815M — EV/EBITDA único método |
| RECV3 | FCF_NEGATIVE_EXPECTED | E&P capex intensivo — EV/EBITDA primário |
| SBSP3 | FCF_NEGATIVE_EXPECTED | Capex de concessão — EV/EBITDA primário |
| VAMO3 | FCF_NEGATIVE_EXPECTED | Leasing intensivo |

---

## Dry-Run Bridge — Resultado Resumido (S05)

| Indicador | Valor |
|-----------|-------|
| Tickers testados via bridge | 18/18 |
| Tickers com fair_value em dry-run | **18/18** |
| write=False respeitado | ✅ |
| valuation_financial_inputs alterada | **Não** |
| asset_intelligence_snapshots alterada | **Não** |
| 401 testes passando | ✅ |

---

## Próximos Passos — M018

```
MILESTONE M018 — Controlled Fair Value Calculation and Validation

Objetivo: Executar modelos M016 com dados reais de valuation_financial_inputs
          e persistir fair_value para 17+ tickers READY_TO_CALCULATE.

Entradas confirmadas:
  - 17 tickers READY_TO_CALCULATE (todos os inputs presentes)
  - 1 ticker PARTIAL_INPUTS (PCAR3 — EV/EBITDA only)
  - Bridge M017-S05 operacional (load_financial_inputs_from_store)
  - 9 PRESERVE_EXISTING intocados

Regras M018:
  - Calcular apenas com dados reais (sem mock, sem estimativa)
  - PRESERVE_EXISTING: não sobrescrever sem force_recalc=True explícito
  - Validar fair_value dentro do range 0.1x–5.0x preço corrente
  - Cruzar com LLM cross-check ±10% vs DCF (P1 pitfall)
  - Persistir com write=True apenas após validação
```

---

*Milestone M017 fechado administrativamente em 2026-05-26.*
*Baseado em: slices S01–S05 · git commit a91223a · 401/401 testes passando.*
*M018 autorizado. Iniciar com: M018-S01 Controlled Fair Value Write.*
