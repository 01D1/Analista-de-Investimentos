# M014 — Valuation Universal: Sector Router + Stores Canônicos

**Data:** 2026-05-25 | **Milestone:** M014 | **Status:** ✅ Fechado

## One-liner

Arquitetura e implementação de roteamento metodológico (sector router) + 4 stores canônicos de valuation. Conecta CVM ingestion (M011) ao pipeline de valuation, coexiste com M012/M013 via D086, preserva D077-D082 integralmente.

---

## Resumo por Slice

| Slice | Título | Status | Key Deliverable |
|-------|--------|--------|-----------------|
| S01 | Auditoria de Cobertura | ✅ | docs/coverage_audit_20260523.csv — 9 tickers auditados, 0 READY |
| S02 | Matriz de Cobertura Operacional | ✅ | pages/valuation_coverage.py + 4 NEEDS_DATA/4 PARTIAL/0 READY |
| S02.5 | Universe Expansion Audit | ✅ | 34 candidatos, 29 NEEDS_CVM_DATA, 5 NEEDS_SECTOR, 0 ELIGIBLE_NOW |
| S03 | Arquitetura de Valuation Universal | ✅ | M014-ARCHITECTURE.md — 5 camadas, 3 contratos, D083-D088 |
| S04 | Sector Router Universal | ✅ | src/valuation/router.py — 8 setores, 57/57 testes |
| S05 | Stores Canônicos de Valuation | ✅ | 4 stores + unified API — 28/28 testes |

---

## Decisões Arquiteturais (D083-D092)

| ID | Decisão | Status |
|----|---------|--------|
| D083 | 5-camadas: Ingestion → Setorização → Router → Engine → Stores | ✅ |
| D084 | method_suggested (router) ≠ method_used (engine) | ✅ |
| D085 | fundamental_quality_score = output do motor, não estimado | ✅ |
| D086 | Stores coexistem com valuation_connector.py (M012/M013) | ✅ |
| D087 | NEEDS_CVM_DATA + NEEDS_SECTOR bloqueiam routing | ✅ |
| D088 | Preservação integral de D077-D082 | ✅ |
| D092 | Fallback outputs/ aceito temporariamente (human approved) | ✅ |

---

## Arquivos Criados| Slice | Arquivo | Size |
|---|---------|-------|
| S01 | docs/coverage_audit_20260523.csv | 37 cols, 9 rows |
| S01 | docs/coverage_audit_README.md | documentação completa |
| S02 | src/fundamentals/valuation_coverage.py | CoverageStatus + classify |
| S02 | pages/valuation_coverage.py | página Streamlit |
| S03 | M014-ARCHITECTURE.md | 15 527 bytes |
| S04 | src/valuation/router.py | 8 776 bytes |
| S04 | tests/test_router.py | 22 318 bytes (57 testes) |
| S05 | src/valuation/valuation_results.py | 9 400 bytes |
| S05 | src/valuation/valuation_inputs.py | 8 200 bytes |
| S05 | src/valuation/valuation_coverage.py | 8 300 bytes |
| S05 | src/valuation/valuation_store.py | 7 700 bytes |
| S05 | src/valuation/__init__.py | 2 300 bytes |
| S05 | tests/test_valuation_stores.py | 8 800 bytes (28 testes) |

**Total:** 13 arquivos criados, 0 modificados no código existente de M012/M013.

---

## Validações Finais

| Verificação | Resultado |
|-------------|-----------|
| py_compile (6 arquivos S05) | ✅ OK |
| imports (router + 4 stores + API pública) | ✅ OK |
| pytest S04: 57/57 | ✅ PASSED |
| pytest S05: 28/28 | ✅ PASSED |
| valuation_connector.py intacto (PETR4=81.12) | ✅ PASS |
| Router PETR4: DCF, blocked=False, confidence=1.0 | ✅ PASS |
| Stores PETR4/BBAS3/ITUB4/WEGE3 preservados | ✅ PASS |
| Empty ticker → None, not 0.0 (VALUATION_MISSING) | ✅ PASS |
| save_valuation_result stub (sempre False) | ✅ PASS |
| app.py + pages/valuation_engine + pages/radar_ai | ✅ PASS |
| D077-D082 preservados (nenhum store calcula valuation) | ✅ PASS |
| D086 coexistência: connector + stores coexistem | ✅ PASS |
| D092 fallback outputs/ transitório | ✅ PASS |

**Total: 85/85 verificações passando.**

---

## Estado do Universo Post-M014

| Status | Count | Tickers |
|--------|-------|---------|
| READY (valuation completo) | 0 | — |
| PARTIAL (fair_value existe, método/FQS ausentes) | 4 | PETR4, BBAS3, ITUB4, WEGE3 |
| NEEDS_MODEL (flag=1, sem fair_value) | 1 | BBDC4 |
| NEEDS_CVM_DATA | 29 | universo expandido |
| NEEDS_SECTOR | 5 | universo expandido |
| EMPTY | 0 | — |

**Caminho para READY:** CVM ingestion (M011) → setorização (AI entry) → coverage → router → valuation engine (S06).

---

## O que foi excluído do scope

- ❌ Cálculo DCF/COSIF/DDM (M015)
- ❌ Motor fundamentalista (M016)
- ❌ Modificação de M011/M012/M013
- ❌ Alteração de opções/OOS/paper/scheduler
- ❌ Alteração de frontend (exceto pages/valuation_coverage.py criado em S02)
- ❌ Dados mockados
- ❌ Alteração de banco manualmente

---

## Próximos Marcos

| ID | Título | Dependência |
|----|--------|-------------|
| M011 | CVM/RI Ingestion | M014 (setorização downstream) |
| M015 | Valuation Engine | M014 (router + stores) |
| M016 | Fundamental Quality Score | M011 (CVM data) |

---

*Milestone fechado. S01-S05 concluídas e registradas. M014 pronto para archivamento.*