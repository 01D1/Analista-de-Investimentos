# M017-S04 — Summary

**Status:** ✅ CONCLUÍDO  
**Data:** 2026-05-26  
**Duração:** ~60 min

## Objetivo

Avaliar se os 18 tickers NEEDS_FINANCIALS possuem inputs suficientes para os modelos
M016 do `scanner_quant_profit_b3`, sem calcular fair_value e sem sobrescrever valores existentes.

## O que foi feito

### 1. Leitura e análise de valuation_financial_inputs (pré-S04)

- 18/18 tickers presentes na tabela
- 21 métricas por ticker (CVM_CSV, source_priority=1)
- `shares_outstanding`: ausente para todos os 18 tickers — gap herdado de S03

### 2. Geração da matriz ticker × métrica

- 15 métricas-chave verificadas: revenue, ebit, ebitda, net_income, ocf, capex, fcf,
  total_assets, cash, stdebt, ltdebt, gross_debt, net_debt, equity_book_value, shares
- 14/15 métricas presentes para todos os 18 tickers (pré-S04)
- `shares_outstanding` = único gap

### 3. Classificação dos tickers

**Pré-S04:** 18/18 → NEEDS_SHARES  
**Pós-S04:** 17/18 → READY_TO_CALCULATE | 1/18 → PARTIAL_INPUTS (PCAR3)

### 4. Adição de shares_outstanding via yfinance

```
Source: yfinance → .SA suffix, sharesOutstanding field
Source_type: B3_MARKET_DATA
Source_priority: 3
Confidence: 0.85
Period_end: 2025-12-31
```

18 registros inseridos com write=True. Banco: 47.621 total (47.603 de S03 + 18 de S04).

| Ticker | Shares (unidades) |
|--------|------------------:|
| PRIO3 | 804.283.501 |
| RECV3 | 292.999.070 |
| EGIE3 | 1.142.298.836 |
| SBSP3 | 3.506.733.260 |
| TAEE11 | 344.498.907 |
| AZZA3 | 202.024.835 |
| LREN3 | 976.325.259 |
| MGLU3 | 774.905.918 |
| PCAR3 | 491.936.785 |
| VIVA3 | 235.071.814 |
| FLRY3 | 543.624.980 |
| HYPE3 | 703.992.255 |
| KLBN11 | 1.214.936.096 |
| RADL3 | 1.748.536.237 |
| RAIL3 | 1.855.685.680 |
| RENT3 | 1.054.944.417 |
| SUZB3 | 1.236.045.522 |
| VAMO3 | 1.221.826.865 |

### 5. Diagnose dos modelos M016 (write=False)

Todos os 4 modelos executados:
- `diagnose_commodity_tickers(['PRIO3', 'RECV3'])` → NEEDS_FINANCIALS (gap bridge)
- `diagnose_utility_tickers(['EGIE3', 'SBSP3', 'TAEE11'])` → NEEDS_FINANCIALS
- `diagnose_retail_tickers(['AZZA3', 'LREN3', 'MGLU3', 'PCAR3', 'VIVA3'])` → NEEDS_FINANCIALS
- `diagnose_industry_tickers(['FLRY3', 'HYPE3', 'KLBN11', 'RADL3', 'RAIL3', 'RENT3', 'SUZB3', 'VAMO3'])` → NEEDS_FINANCIALS

**Gap identificado**: diagnose functions lêem `scanner_quant.db → asset_intelligence_snapshots`,
não `valuation_financial_inputs`. Escopo de S05.

### 6. Testes executados

| Suite | Passando | Falhas |
|-------|:--------:|:------:|
| test_financial_inputs_store | 29/29 | 0 |
| test_commodity_model | 58/58 | 0 |
| test_utility_model | 62/62 | 0 |
| test_retail_model | 57/57 | 0 |
| test_industry_model | 55/55 | 0 |
| test_bank_model | 63/63 | 0 |
| **TOTAL** | **324/324** | **0** |

## Resultado Final

| Indicador | Valor |
|-----------|-------|
| Tickers avaliados | 18/18 |
| Cobertura pós-S04 | **22/22 métricas** |
| Tickers READY_TO_CALCULATE | **17/18** |
| Tickers PARTIAL_INPUTS | **1/18** (PCAR3) |
| Tickers NEEDS_SHARES | **0/18** (resolvido) |
| Fair values calculados | **0** (RULE-01 cumprida) |
| Fair values sobrescritos | **0** (RULE-02 cumprida) |
| Testes passando | **324/324** |

## Flags de Qualidade

| Ticker | Flag | Detalhe |
|--------|------|---------|
| MGLU3 | FCF_REVIEW | OCF=15.7B vs EBITDA=3.2B (4.8× — anomalous) — possível evento WC one-time |
| PCAR3 | DISTRESSED | EBIT=-169M, NI=-815M — EV/EBITDA único método disponível |
| RECV3 | FCF_NEGATIVE_EXPECTED | E&P capex intensivo — EV/EBITDA primário |
| SBSP3 | FCF_NEGATIVE_EXPECTED | Capex de concessão — EV/EBITDA primário |
| VAMO3 | FCF_NEGATIVE_EXPECTED | Leasing intensivo; CD_CVM=024716 confirmado correto |

## Artefatos

- `docs/M017_S04_MODEL_READINESS_REPORT.md` — relatório completo
- `docs/M017_S04_COVERAGE_MATRIX.csv` — matriz 18 tickers × 15 métricas
- `data/ingestion.db → valuation_financial_inputs` — 47.621 registros (22 métricas × 18 + universo S03)

## Gap Arquitetural (Escopo S05)

Os modelos M016 lêem `scanner_quant.db`, não `valuation_financial_inputs`.
S05 cria a bridge: `load_financial_inputs_from_store(ticker)` → hidrata dataclasses → diagnose dry-run.

## Autorização S05

**✅ S05 AUTORIZADA**

Todos os pré-requisitos cumpridos:
- valuation_financial_inputs completo (22 métricas × 18 tickers)
- 17/18 tickers READY_TO_CALCULATE
- 0 fair_values calculados ou sobrescritos
- 324/324 testes passando
