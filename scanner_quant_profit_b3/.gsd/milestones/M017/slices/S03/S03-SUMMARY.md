# M017-S03 — Summary

**Status:** ✅ CONCLUÍDO
**Data:** 2026-05-26
**Duração:** ~90 min

## Objetivo

Criar o Metric Extraction Engine que lê `cvm_statements` e popula
`valuation_financial_inputs` com 21 métricas financeiras estruturadas
para 88 tickers do universo B3.

## O que foi feito

### 1. Bug fix — parse_and_store() KeyError: 'CD_CVM'
Adicionado `if "CD_CVM" not in df.columns: continue` em
`src/ingestion/cvm_downloader.py:247` para pular o arquivo de metadados
`dfp_cia_aberta_{year}.csv` que não possui a coluna CD_CVM.

### 2. src/ingestion/metric_extractor.py (criado)
Engine principal com:
- **Estratégia de dedup**: `year = YEAR(reference_date)` filtra apenas
  linhas ÚLTIMO de cada exercício, eliminando duplicatas de DFPs cruzados
- **Extração estruturada**: BPA, BPP, DRE com código CVM + validação de nome
- **Extração keyword**: D&A em `6.01.01.xx`, CapEx em `6.02.xx` (outflows negativos)
- **Bancos (COSIF)**: equity via keyword, sem debt breakdown
- **Derivações**: ebitda, gross_debt, net_debt, free_cash_flow, total_liabilities

### 3. run_extract_metrics.py (criado)
CLI runner com modos: `--canary`, `--needs-financials`, `--all`, `--tickers`

### 4. Execução

| Fase | Tickers | Records | Erros |
|------|---------|---------|-------|
| Canário (EGIE3) | 1 | 588 | 0 |
| 18 NEEDS_FINANCIALS | 18 | 9.223 | 0 |
| Batch amplo | 89 | 47.603 | 1 (AUAU3) |

## Resultado Final

| Indicador | Valor |
|-----------|-------|
| Total registros | **47.603** |
| Tickers cobertos | **88/89** (99%) |
| Métricas distintas | **21** |
| Cobertura completa (21/21) | 68 tickers (77%) |
| Cobertura parcial | 20 tickers (23%) |
| Cobertura mínima key metrics | **99%** |

## Métricas extraídas

**Diretas (16):** total_assets, current_assets, cash_and_equivalents,
financial_applications, non_current_assets, current_liabilities,
non_current_liabilities, short_term_debt, long_term_debt, equity_book_value,
revenue, ebit, net_income, operating_cash_flow, depreciation_amortization, capex

**Derivadas (5):** gross_debt, net_debt, ebitda, free_cash_flow, total_liabilities

## Gaps conhecidos

- `shares_outstanding`: não disponível em CVM — pendente para S04 via yfinance
- AUAU3: sem código CVM — 0 registros
- Bancos: sem debt breakdown (COSIF) — 12 tickers com 14/21 métricas
- Seguradoras (BBSE3, IRBR3): sem debt padrão — 17/21 métricas

## Artefatos

- `12_PYTHON/src/ingestion/metric_extractor.py`
- `12_PYTHON/src/ingestion/cvm_downloader.py` (bug fix)
- `12_PYTHON/run_extract_metrics.py`
- `12_PYTHON/docs/M017_S03_METRIC_EXTRACTION_REPORT.md`
- `data/ingestion.db → valuation_financial_inputs` (47.603 rows)

## Autorização S04

**✅ S04 autorizada** — valuation_financial_inputs populado, 99% cobertura,
21 métricas disponíveis, todas derivações calculadas, source_priority=1.
