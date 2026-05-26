# M017 — Fechamento Administrativo

**Data:** 2026-05-26  
**Status:** ✅ FECHADO (administrativamente)  
**Verdict:** ✅ PASS

---

## Autorização

Usuário autorizou o fechamento do M017 após conclusão da S05 (Financial Inputs Bridge).
Instrução explícita: *"Feche administrativamente o M017."*

Condições atendidas: bridge operacional, 18/18 tickers produzem `fair_value` em dry-run
(write=False), 401/401 testes passando, 0 dados salvos, 0 mocks criados, 0 fair_values
calculados, 0 alterações em opções/OOS/paper/scheduler.

---

## Slices — Status Final

| Slice | Título | Status | Método de Fechamento |
|-------|--------|:------:|---------------------|
| S01 | Financial Inputs Schema | ✅ | `valuation_financial_inputs` DDL + `FinancialInputsStore` + 29 testes |
| S02.5 | CVM Dataset Expansion | ✅ | Download universo amplo; relatório cobertura; gap cloud-only descoberto |
| S02.6 | CVM Code Correction | ✅ | Purge 9.407 linhas EQTL3/VAMO3 + reingestão CD_CVM corretos; 1.150.497 válidas |
| S03 | Metric Extraction Engine | ✅ | `metric_extractor.py`; 21 métricas; 47.603 registros; 88/89 tickers |
| S04 | Shares Outstanding | ✅ | yfinance → 18 registros; 47.621 total; 17/18 READY_TO_CALCULATE |
| S05 | Financial Inputs Bridge | ✅ | `financial_inputs_bridge.py`; 18/18 dry-run OK; 401 testes; write=False |

---

## Entregas Consolidadas

### Código

| Arquivo | Tipo | Slice |
|---------|------|-------|
| `src/ingestion/valuation_financial_inputs.py` | CRIADO | S01 |
| `src/ingestion/financial_inputs_store.py` | CRIADO | S01 |
| `src/ingestion/cvm_downloader.py` | ALTERADO | S03 (fix KeyError: CD_CVM) |
| `src/ingestion/metric_extractor.py` | CRIADO | S03 |
| `src/valuation/financial_inputs_bridge.py` | CRIADO | S05 |
| `src/valuation/__init__.py` | ALTERADO | S05 (exports bridge) |

### Testes

| Arquivo | Testes | Slice |
|---------|:------:|-------|
| `tests/test_financial_inputs_store.py` | 29 | S01 |
| `tests/test_financial_inputs_bridge.py` | ~77 | S05 |
| **Total novos M017** | **~106** | S01 + S05 |

### Documentação

| Arquivo | Slice |
|---------|-------|
| `12_PYTHON/docs/M017_S02.6_CVM_CODE_CORRECTION_REPORT.md` | S02.6 |
| `12_PYTHON/docs/M017_S04_MODEL_READINESS_REPORT.md` | S04 |
| `12_PYTHON/docs/M017_S04_COVERAGE_MATRIX.csv` | S04 |
| `12_PYTHON/docs/M017_S05_DRY_RUN_MATRIX.csv` | S05 |
| `.gsd/milestones/M017/M017-SUMMARY.md` | Fechamento |
| `.gsd/milestones/M017/M017-VALIDATION.md` | Fechamento |
| `.gsd/milestones/M017/M017-CLOSED.md` | **Este arquivo** |

---

## Estado do Universo Post-M017 (32 tickers ativos)

| Status | Count | Tickers |
|--------|------:|---------|
| PRESERVE_EXISTING | 9 | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11, PETR4, WEGE3 |
| READY_TO_CALCULATE | 17 | PRIO3, RECV3, EGIE3, SBSP3, TAEE11, AZZA3, LREN3, MGLU3, VIVA3, FLRY3, HYPE3, KLBN11, RADL3, RAIL3, RENT3, SUZB3, VAMO3 |
| PARTIAL_INPUTS | 1 | PCAR3 (DISTRESSED — EV/EBITDA only) |
| TECH_FALLBACK | 1 | VIVT3 |
| NEEDS_DATA | 1 | VALE3 (ri_docs=0) |
| NEEDS_RI_DOCS | 2 | AUAU3, NTCO3 |
| LEGACY_TICKER | 1 | PETZ3 (permanentemente bloqueado) |

> **18 tickers estão prontos para calcular fair_value em M018.**  
> **9 fair values auditáveis preservados. Nenhum sobrescrito. Nenhum calculado sem dados reais.**

---

## Validações Finais

| Verificação | Resultado |
|-------------|:---------:|
| `valuation_financial_inputs`: 47.621 registros (21 métricas × 88 tickers + shares) | ✅ |
| 18/18 tickers → dry-run fair_value via bridge (write=False) | ✅ |
| `asset_intelligence_snapshots`: inalterado | ✅ |
| `cvm_statements`: 1.150.497 linhas com CDs corretos | ✅ |
| EQTL3/VAMO3 dados limpos (purge + reingestão correta) | ✅ |
| PRESERVE_EXISTING: 9 fair values intocados | ✅ |
| D117 cumprida: 0 fair_values calculados com write=True | ✅ |
| 401/401 testes passando | ✅ |
| 0 mocks criados | ✅ |
| 0 alterações opções/OOS/paper/scheduler | ✅ |

**Total: 10/10 verificações.**

---

## Próximos Passos — M018

```
MILESTONE M018 — Controlled Fair Value Calculation and Validation

Objetivo: Executar modelos M016 com inputs reais de valuation_financial_inputs,
          persistir fair_value para 17+ tickers, e validar outputs.

Slices sugeridos:
  M018-S01: Execução controlada — commodity + utility (5 tickers)
  M018-S02: Execução controlada — retail + industry (12 tickers, incl. PCAR3)
  M018-S03: Validação cruzada (range 0.1x–5.0x price; cross-check DCF ±10%)
  M018-S04: Persistência com write=True + snapshot asset_intelligence

Resultado esperado: ≥ 17 fair_values reais persistidos; cobertura M016 + M015
                    completamente realizada; plataforma pronta para síntese LLM.

Restrições M018:
  - PRESERVE_EXISTING (9 tickers): não alterar sem force_recalc=True explícito
  - PCAR3: EV/EBITDA only (DISTRESSED flag)
  - Cross-check obrigatório: fair_value dentro do range 0.1×–5.0× preço atual
  - LLM não calcula — injeta apenas números do Financial Engine (P1 pitfall)
```

---

*Milestone M017 fechado administrativamente em 2026-05-26.*  
*Baseado em: M017-S05 · git commit a91223a · M017_S05_DRY_RUN_MATRIX.csv · 401/401 testes.*  
*M018 autorizado. Iniciar com: `/gsd-discuss-phase M018` ou `M018-S01 Commodity + Utility`.*
