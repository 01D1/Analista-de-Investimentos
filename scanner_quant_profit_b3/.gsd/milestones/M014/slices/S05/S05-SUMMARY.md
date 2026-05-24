# S05 — Canonical Valuation Stores

**Data:** 2026-05-25 | **Slice:** S05 | **Milestone:** M014 | **Status:** ✅ Completada

## One-liner

Implementação de 4 stores canônicos de valuation (results/inputs/coverage + unified store) com interface pública tipada, fallback outputs/ transitório, coexistência com valuation_connector.py, e 28/28 testes passando.

---

## Arquivos Criados

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `src/valuation/valuation_results.py` | 9.4 KB | Store canônico: fair_value, upside, método, confiança |
| `src/valuation/valuation_inputs.py` | 8.2 KB | Store canônico: setor, subsector, coverage, scores |
| `src/valuation/valuation_coverage.py` | 8.3 KB | Store canônico: status por ticker + ri_docs_count |
| `src/valuation/valuation_store.py` | 7.7 KB | Interface unificada + shim compat M012/M013 |
| `src/valuation/__init__.py` | 2.3 KB | Re-export unificado de toda API pública |
| `tests/test_valuation_stores.py` | 8.8 KB | 28 testes unitários cobrindo todos os requisitos |

---

## Interface Pública Implementada

```
load_valuation_result(ticker)           → ValuationResult (fair=None se sem dados)
list_valuation_results(tickers)         → pd.DataFrame (colunas canônicas)
load_valuation_fair_values(tickers)     → pd.DataFrame (mínimo: ticker, fair, upside)
load_valuation_inputs(ticker)            → ValuationInputs (coverage_status inferido)
list_valuation_inputs(tickers)           → pd.DataFrame
load_valuation_coverage(ticker)          → ValuationCoverage (status + ri_docs_count)
load_valuation_coverage_batch(tickers)   → pd.DataFrame (todos, inclui empty)
save_valuation_result(...)               → bool STUB (sempre False, não usado)
load_latest_valuation_data(tickers)      → pd.DataFrame (shim compat connector)
```

---

## Fontes de Dados (por Precedência)

1. `asset_intelligence_snapshots` (banco SQLite) — fonte primária quando populated
2. `outputs/Valuation_TICKER_*.xlsx` (pipeline legacy) — **fallback transitório** até CVM ingestion

**Nota (D092):** Fallback outputs/ é aceito temporariamente. Não cria valuation novo, não sobrescreve dados canônicos futuros, não viola D077-D082.

---

## Validações Executadas

| Verificação | Resultado |
|-------------|-----------|
| py_compile src/valuation/*.py | ✅ ALL OK |
| import todos os stores + API pública | ✅ ALL OK |
| valuation_connector.py intacto | ✅ PETR4=81.12 preservado |
| PETR4/BBAS3/ITUB4/WEGE3 dados preservados | ✅ Fair values e método intactos |
| Ticker sem dados → None, não 0.0 | ✅ VALUATION_MISSING + fair_value=None |
| Router coexiste (PETR4→DCF, blocked=False, conf=1.0) | ✅ Inalterado |
| save_valuation_result stub (sempre False) | ✅ OK |
| app.py importa sem erro | ✅ OK |
| pages/valuation_engine importa sem erro | ✅ OK |
| pages/radar_ai importa sem erro | ✅ OK |
| pytest 28/28 | ✅ PASSED |

---

## Testes (28/28 verdes)

- Imports: 5 testes (stores individuais + API pública completa)
- Empty sentinel: 4 testes (None≠0.0, VALUATION_MISSING, factory, omitidos do fair_values)
- Preserved data: 5 testes (PETR4/BBAS3/ITUB4/WEGE3 + batch)
- Router coexistence: 4 testes (routed/blocked/confidence/empty batch)
- Inputs store: 3 testes (load/list/empty)
- Save stub: 2 testes (retorna False, não crasha)
- Compat shim: 3 testes (DataFrame/governance/preserved data)
- Column contracts: 2 testes (result/coverage columns)

---

## Coexistência com valuation_connector.py

```
valuation_connector.py (M012/M013)  → lê outputs/ diretamente (backup)
stores canônicos S05               → lê asset_intelligence + outputs/ fallback
load_latest_valuation_data (store) → shim que adapta stores → formato connector
```

- valuation_connector.py **não foi modificado** — zero regressão
- D077-D082 intocados
- D086 (coexistência) respeitado
- D092 (fallback transitório) registrado

---

## Riscos Remanescentes

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| asset_intelligence_snapshots vazio em produção | Baixo | Fallback outputs/ cobre PETR4/BBAS3/ITUB4/WEGE3 |
| Outputs path quebrando com cwd | Baixo | SCANNER_QUANT_DB env var respeitada |
| save_valuation_result stub sendo chamado | Baixo | Retorna False sem side-effects |
| ri_docs_count = 0 quando banco populado | Baixa | Coverage status inferido por dados disponíveis |

---

## O que não foi feito (fora do scope)

- ❌ Cálculo DCF/COSIF/DDM (S06+)
- ❌ Criação de fair_value novo
- ❌ Alteração de banco manualmente
- ❌ Alteração de valuation_connector.py
- ❌ Alteração de opções/OOS/paper/scheduler
- ❌ Dados mockados
- ❌ DCF pesado (S06+)

---

## Verificação

- ✅ 4 stores canônicos criados, compilando e exportando
- ✅ 28/28 testes passando
- ✅ API pública completa com tipos tipados (ValuationResult/Inputs/Coverage)
- ✅ Ticker sem dados → None/VALUATION_MISSING, não R$ 0,00 falso
- ✅ save_valuation_result stub exposto (sempre False)
- ✅ valuation_connector.py intacto (PETR4=81.12)
- ✅ router (S04) coexiste sem alteração
- ✅ app/pages não quebrados
- ✅ D077-D082 e D092 respeitados

---

*Slice concluída. M014 pronto para fechamento.*