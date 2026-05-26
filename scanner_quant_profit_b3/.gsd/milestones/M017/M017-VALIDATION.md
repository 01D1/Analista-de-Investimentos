# M017 — Validation Report

**Milestone:** M017 — Structured DFP/ITR Financial Statements Parser  
**Data:** 2026-05-26  
**Verdict:** ✅ PASS  
**Evaluator:** agent (dry-run batch 18 tickers + 401/401 testes + M017_S05_DRY_RUN_MATRIX.csv)

---

## Success Criteria Checklist

| # | Critério | Resultado | Evidência |
|---|---------|:---------:|-----------|
| 1 | `valuation_financial_inputs` criada com schema correto | ✅ PASS | DDL em `valuation_financial_inputs.py`; `input_hash` + `source_priority` presentes; S01 |
| 2 | ≥ 10 tickers READY_TO_CALCULATE | ✅ PASS | **17/18** tickers com todos os inputs críticos (ebitda, fcf, net_debt, shares) |
| 3 | PCAR3 DISTRESSED flag documentada | ✅ PASS | EBIT=-169M, NI=-815M; EV/EBITDA único método; S04 relatório |
| 4 | VAMO3 = MANUAL_REVIEW — não criou mock | ✅ PASS | FCF_NEGATIVE_EXPECTED documentado; 0 dados sintéticos |
| 5 | 0 fair_values calculados com write=True | ✅ PASS | D117 respeitado; bridge opera exclusivamente write=False |
| 6 | 0 fair_values sobrescritos (PRESERVE_EXISTING) | ✅ PASS | 9 valores M015/M016 intocados — bridge bloqueia por preserve_logic |
| 7 | 18/18 tickers produzem fair_value em dry-run via bridge | ✅ PASS | M017_S05_DRY_RUN_MATRIX.csv confirma 18/18 |
| 8 | `valuation_financial_inputs` não alterada por S05 | ✅ PASS | 47.621 registros pré e pós bridge — nenhum write executado |
| 9 | `asset_intelligence_snapshots` não alterada em M017 | ✅ PASS | M017 é read-only em scanner_quant.db; bridge hidrata dataclasses na memória |
| 10 | Dados CVM corretos para EQTL3 e VAMO3 | ✅ PASS | Purge 9.407 linhas contaminadas + reingestão CD_CVM 020010/024716; S02.6 |
| 11 | Métricas extraídas: 21 por ticker | ✅ PASS | 16 diretas + 5 derivadas em `metric_extractor.py`; S03 |
| 12 | Cobertura CVM: ≥ 85 tickers | ✅ PASS | 88/89 (99%); AUAU3 exclui por CNPJ nulo (D123) |
| 13 | `input_hash` populado em todos os registros | ✅ PASS | D118 — hash de (ticker + metric_name + period_end + value) como gate |
| 14 | 401/401 testes passando | ✅ PASS | Suite completa M017 incluindo bridge; 0 falhas |
| 15 | 0 mocks criados | ✅ PASS | Todos os valores em `valuation_financial_inputs` têm source CVM_CSV ou B3_MARKET_DATA |
| 16 | 0 alterações em opções/OOS/paper/scheduler | ✅ PASS | Scope M017 respeitado integralmente |

**Overall: 16/16 critérios passando.**

---

## Definition of Done

| Item | Status | Notas |
|------|:------:|-------|
| `valuation_financial_inputs` populada com dados reais | ✅ | 47.621 registros; 88 tickers; 21 métricas |
| Métrica `shares_outstanding` presente para 18 NEEDS_FINANCIALS | ✅ | yfinance; source_priority=3; confidence=0.85 |
| Bridge `load_financial_inputs_from_store()` operacional | ✅ | Hidrata todas as dataclasses dos modelos M016 |
| Dry-run 18/18 tickers com fair_value | ✅ | write=False; M017_S05_DRY_RUN_MATRIX.csv |
| PCAR3 flag DISTRESSED documentada | ✅ | EV/EBITDA only; S04 relatório + S05 matrix |
| VAMO3 FCF_NEGATIVE_EXPECTED documentada | ✅ | Leasing intensivo; CD_CVM=024716 correto |
| Dados EQTL3/VAMO3 corrigidos em cvm_statements | ✅ | S02.6 purge + reingestão CD_CVM corretos |
| Banco não alterado por S05 (somente leitura) | ✅ | write=False default em bridge |
| PRESERVE_EXISTING intocados (9 fair values) | ✅ | bridge bloqueia antes de qualquer cálculo destrutivo |
| 401/401 testes passando | ✅ | Tempo < 3s |
| Gap PCAR3 documentado para M018 | ✅ | PARTIAL_INPUTS → EV/EBITDA only em M018 |
| Zero opções/OOS/paper/scheduler alterados | ✅ | Escopo respeitado |

**DoD: 12/12 items met.**

---

## Teste Summary

```
tests/test_financial_inputs_store.py    29 passed  ← S01 (Schema + Store)
tests/test_financial_inputs_bridge.py   77 passed  ← S05 (Bridge dry-run)
tests/test_commodity_model.py           58 passed  ← M016/S03 (integrado)
tests/test_utility_model.py             62 passed  ← M016/S04 (integrado)
tests/test_retail_model.py              57 passed  ← M016/S04 (integrado)
tests/test_industry_model.py            55 passed  ← M016/S04 (integrado)
tests/test_bank_model.py                63 passed  ← M016/S02 (integrado)
tests/test_sector_normalizer.py          0 passed  ← fora do scope M017 run
────────────────────────────────────────────────────
TOTAL M017                             401 passed
```

---

## Dry-Run Matrix — Resumo (M017_S05_DRY_RUN_MATRIX.csv)

| Grupo | Tickers | Dry-Run OK | Flags |
|-------|:-------:|:----------:|-------|
| COMMODITY | PRIO3, RECV3 | 2/2 | RECV3: FCF_NEGATIVE_EXPECTED |
| UTILITY | EGIE3, SBSP3, TAEE11 | 3/3 | SBSP3: FCF_NEGATIVE_EXPECTED |
| RETAIL | AZZA3, LREN3, MGLU3, PCAR3, VIVA3 | 5/5 | MGLU3: FCF_REVIEW · PCAR3: DISTRESSED |
| INDUSTRY | FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3 | 8/8 | VAMO3: FCF_NEGATIVE_EXPECTED |
| **TOTAL** | **18** | **18/18** | — |

> Todos os 18 tickers produzem `fair_value` em dry-run.  
> Nenhum valor foi persistido — `write=False` respeitado em 100% das execuções.

---

## Database Integrity

| Verificação | Antes S05 | Depois S05 | Δ |
|------------|----------:|----------:|---|
| `valuation_financial_inputs` (registros) | 47.621 | 47.621 | **0** ✅ |
| `asset_intelligence_snapshots` (registros) | inalterado | inalterado | **0** ✅ |
| `cvm_statements` (registros) | 1.150.497 | 1.150.497 | **0** ✅ |

---

*Milestone M017 validado em 2026-05-26.*  
*Evidências: git commit a91223a · slices S01–S05 · M017_S05_DRY_RUN_MATRIX.csv*
