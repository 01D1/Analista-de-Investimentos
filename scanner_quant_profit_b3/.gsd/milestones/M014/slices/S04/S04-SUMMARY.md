# S04 — Universal Sector Router Implementation

**Data:** 2026-05-25 | **Slice:** S04 | **Milestone:** M014 | **Status:** ✅ Completada

## One-liner

Implementação do sector router universal como camada de roteamento metodológico: dado ticker + setor + coverage status, retorna `RouterDecision` com método sugerido, confiança e regras de bloqueio — sem valuation, sem mocks, sem alteração de banco.

---

## O que foi entregue

### Arquivos criados

| Arquivo | Tamanho | Propósito |
|---------|---------|-----------|
| `src/valuation/router.py` | 8 776 bytes | Sector router universal (S04) |
| `tests/test_router.py` | 22 318 bytes | 57 testes cobrindo todos os requisitos |

### Classes e funções implementadas

- `ValuationMethod` — enum com 9 métodos (COSIF_DDM, DDM, DCF, NAV, RAB, EV_EBITDA, RELATIVOS, SOTP, UNKNOWN)
- `RoutingStatus` — enum (ROUTED, BLOCKED, UNAVAILABLE)
- `Provenance` — dataclass com source/date/analyst_override
- `RouterDecision` — dataclass com 10 campos (ticker, sector, coverage_status, method_suggested, blocked, block_reason, confidence, provenance_source, notes, method_alternatives)
- `get_valuation_method()` — ponto de entrada público

---

## Mapeamento Setor → Método

| Setor | Método Primário | Alternativas | Confiança |
|-------|----------------|--------------|-----------|
| BANK | COSIF/DDM | DCF | 1.0 |
| INSURANCE | DDM | EV/EBITDA | 1.0 |
| COMMODITY | DCF | EV/EBITDA | 1.0 |
| UTILITY | DCF | RAB | 1.0 |
| INDUSTRY | DCF | EV/EBITDA | 1.0 |
| RETAIL | DCF | EV/EBITDA | 1.0 |
| HOLDING | NAV | DCF | 1.0 |
| TECH | DCF | SOTP | 1.0 |
| FALLBACK_MULTIPLES | RELATIVOS | — | 0.5 |

---

## Regras de Bloqueio (D087 implementadas)

| Condição | Comportamento |
|----------|--------------|
| `coverage_status = needs_data` | `blocked=True`, `block_reason="NEEDS_CVM_DATA"`, `confidence=0.0` |
| `coverage_status = needs_sector` | `blocked=True`, `block_reason="NEEDS_SECTOR"`, `confidence=0.0` |
| `provenance.source != "TRACEABLE"` | `blocked=True`, `block_reason="NEEDS_SECTOR"`, `confidence=0.0` |

**D084 implementado:** `RouterDecision.method_suggested` — `method_used` fica no `ValuationResult` (S06+).

---

## Testes Executados

```
tests/test_router.py — 57 passed in 0.06s

Suite 1: Sector Routing (9 casos)
  ✅ 8 setores primários (BANK→TECH) — todas alternativas cobridas
  ✅ FALLBACK: setor desconhecido → RELATIVOS, confidence=0.5
  ✅ Fallback com sector=None → RELATIVOS
  ✅ Fallback com sector="" → RELATIVOS
  ✅ Case insensitive (bank → BANK)

Suite 2: Bloqueio NEEDS_CVM_DATA (5 testes)
  ✅ needs_data → blocked + block_reason correto
  ✅ Bloqueio não depende de setor
  ✅ Ticker/setor preservados no bloqueio

Suite 3: Bloqueio NEEDS_SECTOR (2 testes)
  ✅ needs_sector → blocked + block_reason correto
  ✅ Ticker preservado no bloqueio

Suite 4: Bloqueio Provenance (5 testes)
  ✅ source=UNKNOWN → bloqueado
  ✅ source=MANUAL → bloqueado
  ✅ source=None → bloqueado
  ✅ source=TRACEABLE → permite routing
  ✅ Provenance vence coverage_status=ready

Suite 5: method_suggested ≠ method_used (3 testes)
  ✅ RouterDecision tem method_suggested, não method_used
  ✅ method_suggested corresponde à tabela de routing
  ✅ Decisão bloqueada → method=UNKNOWN

Suite 6: Confiança e Notas (7 testes)
  ✅ ready + TRACEABLE → confidence=1.0
  ✅ partial + TRACEABLE → confidence=1.0
  ✅ blocked → confidence=0.0
  ✅ FALLBACK → confidence=0.5
  ✅ Notes contém info de routing
  ✅ Provenance propagado na decisão

Suite 7-9: Normalização, Integração, Estrutura (21 testes)
  ✅ Ticker case/espaços normalizados
  ✅ Coverage status como string (não importa enum)
  ✅ Todos campos obrigatórios presentes
  ✅ blocked=True → block_reason != None
  ✅ blocked=False → block_reason == None
```

---

## Validações de Integração

```
✅ Router imports OK
✅ Router PETR4: method=DCF, blocked=False, confidence=1.0
✅ Coverage PETR4: partial (classify_coverage intacta)
✅ Valuation connector: load_fair_values intacta (1 row)
✅ M011/M012/M013 não quebrados
```

---

## S05 Authorization Assessment

### Status: ✅ AUTORIZADA COM PRUDÊNCIA

S05 (stores canônicos) pode prosseguir nas condições abaixo:

**Condições de prosseguimento:**
1. `valuation_store.py` coexiste com `valuation_connector.py` (D086)
2. `valuation_results` usa a estrutura `RouterDecision.method_suggested` como input
3. Store não escreve em `outputs/` (preserva D077-D082)
4. Testes cobrem CRUD de store + integração com router
5. Dashboard lê de novo store E de connector antigo (dual-read pattern)

**Blockers removidos:**
- S04 router já existe e está testado (57 testes verdes)
- Arquitetura define coexistência clara (D086)
- Contrato público entre router e store definido (M014-ARCHITECTURE.md seção 5)

**Riscos remanescentes para S05:**
| Risco | Prob. | Mitigação |
|-------|-------|-----------|
| Store sobrescreve outputs/ | Baixa | D086 coexistência; store lê apenas |
| Dashboard coupling com store | Média | Dual-read pattern; connector antigo preservado |
| Integração com router não testada | Alta | S05 testes devem cobrir router→store |

---

## Riscos Remanescentes

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Provenance source não populado nos dados reais | Alta | Alta | S04 bloqueia corretamente; dependência do upstream |
| Setor mal atribuído bloqueia todos os 5 NEEDS_SECTOR | Alta | Alta | S04 implementa bloqueio; upstream precisa corrigir |
| Ticker sem AI entry → coverage=empty → routed? | Média | Baixa | empty → partial default → routed; OK para router |
| Confiança 0.5 no fallback pode mascarar problemas | Baixa | Média | Notas contém warning; engine (S06+) decide |

---

## O que não foi feito (dentro do scope S04)

- ❌ Cálculo de fair_value (S06+)
- ❌ Execução de DCF/COSIF/DDM (S06+)
- ❌ Alteração de banco (S05)
- ❌ Alteração de frontend (future milestone)
- ❌ Dados mockados
- ❌ Modificação de valuation_connector.py (M012/M013)
- ❌ Alteração de opções/OOS/paper/scheduler

---

## Verificação

- ✅ `src/valuation/router.py` criado com contrato público completo
- ✅ 57 testes passando (8 setores + fallback + bloqueios + D084)
- ✅ Bloqueio NEEDS_CVM_DATA implementado e testado
- ✅ Bloqueio NEEDS_SECTOR implementado e testado
- ✅ `method_suggested` ≠ `method_used` (D084 implementado)
- ✅ Confiança 0.5 para FALLBACK, 1.0 para routed normal, 0.0 para blocked
- ✅ M011/M012/M013 não quebrados (validação de integração OK)
- ✅ Sem mocks, sem valuation, sem alteração de banco

---

*Slice concluída. Próximo passo: S05 — Stores Canônicos.*