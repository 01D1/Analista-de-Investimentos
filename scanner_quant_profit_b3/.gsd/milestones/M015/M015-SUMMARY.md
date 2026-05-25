# M015 — CVM RI Ingestion and Sector Metadata Recovery

**Data:** 2026-05-24 | **Milestone:** M015 | **Status:** ✅ FECHADO

## One-liner

Recuperação completa de dados CVM/RI e metadados setoriais para o universo B3:
3.251 RI docs em 28 tickers, 64/64 AI entries populadas, PETZ3 bloqueado como
LEGACY_TICKER, AUAU3 staged como successor monitorável, fair values preservados
integralmente, e base pronta para M016 Valuation Engine real.

---

## Resumo por Slice

| Slice | Título | Status | Key Deliverable |
|-------|--------|:------:|-----------------|
| S01 | Data Source Traceability Audit | ✅ | Gap breakdown 63 tickers — 57 COTAHIST_NO_AI, 58 TRACE_NO_RI, schema bug market_type catalogado |
| S01.5 | Connector and Schema Diagnosis | ✅ | Roadmap corrigido, INSERT quebrado diagnosticado, 64+1 tickers classificados |
| S03 | AI Entry Creation + Metadata | ✅ | 64/64 AI entries (57 INSERT + 7 UPDATE); sector rastreável=31, UNKNOWN=33, BDR_FII=6 |
| S03.5 | Corporate Actions Patch | ✅ | PETZ3 → LEGACY_TICKER; AUAU3 → successor ativo; ticker_aliases.py criado |
| S02 | CVM RI Ingestion Repair | ✅ | 3.251 RI docs inseridos em 28 tickers; VALE3/NTCO3/PETZ3 = 0 inseridos (sem dados) |
| S04 | Coverage Audit Before/After | ✅ | 626 docs/5 tickers → 3.251 docs/28 tickers; 17/17 validações passando |
| S05 | M016 Readiness Assessment | ✅ | Smoke test 7 tickers; matriz readiness; gap SectorNormalizer identificado |

---

## Decisões Registradas (M015)

| ID | Decisão | Status |
|----|---------|:------:|
| D093 | sector='UNKNOWN' = placeholder técnico; não desbloqueia router | ✅ |
| D094 | PETZ3 = LEGACY_TICKER (fusão Petz+Cobasi 2026-01-02); successor=AUAU3 | ✅ |
| D095 | AUAU3 = successor monitorável; HAS_SECTOR_NO_RI até RI docs disponíveis | ✅ |
| D096 | VALE3/NTCO3 sem RI docs = bloqueio correto (needs_data); não é erro | ✅ |
| D097 | SectorNormalizer (GICS→router key) = S01/P0 de M016 | ✅ |
| D098 | S03 metadata stale (HAS_SECTOR_NO_RI para tickers com docs) = corrigir em M016-S06 | ✅ |

---

## Arquivos Criados / Alterados

| Slice | Arquivo | Descrição |
|-------|---------|-----------|
| S03 | `scripts/m015_s03_ai_entry_population.py` | Script AI entry; 64 entradas |
| S03.5 | `config/ticker_aliases.yaml` | Mapeamento PETZ3→AUAU3 |
| S03.5 | `config/corporate_identity.yaml` | Corporate actions B3 |
| S03.5 | `src/utils/ticker_aliases.py` | LEGACY_TICKERS set; successor_for() |
| S03.5 | `src/valuation/valuation_coverage.py` | CoverageStatus.LEGACY_TICKER adicionado |
| S03.5 | `docs/m015_s035_corporate_action_patch_report.md` | Relatório S03.5 |
| S02 | `scripts/m015_s02_cvm_ri_ingestion_repair.py` | Script CVM ingestion |
| S04 | `docs/m015_s04_coverage_audit_report.md` | Audit before/after |
| S05 | `docs/M015_S05_READINESS_REPORT.md` | Smoke test + matriz readiness |

---

## Estado do Universo Post-M015

| Status | Count | Tickers Representativos |
|--------|------:|------------------------|
| **READY_FOR_MODEL_DESIGN** | 28 | BBAS3, PETR4, ITUB4, SUZB3, BPAC11, WEGE3… |
| **NEEDS_RI_DOCS** | 3 | VALE3, NTCO3, AUAU3 |
| **NEEDS_SECTOR** | 32 | Em AI snapshots; não em tickers.yaml canônico |
| **LEGACY_BLOCKED** | 1 | PETZ3 (→AUAU3) |
| **MANUAL_REVIEW** | 0 | — |

**Fair values preservados:** BBAS3=64,84 · ITUB4=73,69 · PETR4=81,12 · WEGE3=40,16

**RI docs:** 3.251 documentos em 28 tickers (data/database/scanner_quant.db · ri_documents)

---

## Gap Crítico Remanescente — S01/P0 de M016

> **SectorNormalizer:** O router (`src/valuation/router.py`) usa chaves canônicas
> (`BANK`, `COMMODITY`, `UTILITY`…) mas o banco e `tickers.yaml` armazenam valores
> GICS em lowercase (`financials`, `energy`, `materials`…). Sem normalização, todos
> os 28 tickers roteáveis caem em FALLBACK/Relativos com confidence=0.5.
>
> **Fix:** `src/valuation/sector_normalizer.py` — mapeia `type` do tickers.yaml
> para chave canônica do router. Deve ser a **primeira tarefa de M016**.

---

## O que foi excluído do scope

- ❌ Cálculo DCF, COSIF, DDM ou qualquer fair value
- ❌ Alteração de opções / OOS / paper / scheduler
- ❌ Dados mockados
- ❌ Alteração manual de banco
- ❌ Sobrescrita de fair values existentes

---

## Próximos Marcos

| ID | Título | Dependência | Prioridade |
|----|--------|-------------|:----------:|
| **M016** | **Valuation Engine Real** | M015 ✅ | **P0** |
| — | SectorNormalizer (M016-S01) | M015 ✅ | P0 bloqueador |
| — | COSIF/DDM bancos (M016-S02) | M016-S01 | P1 |
| — | DCF/COMMODITY oil_gas (M016-S03) | M016-S01 | P1 |
| — | DCF/INDUSTRY+RETAIL+UTILITY (M016-S04) | M016-S01 | P1 |
| — | Metadata refresh stale (M016-S05/S06) | M016-S01 | P2 |
| — | VALE3/NTCO3/AUAU3 CVM ingestion | M016-SXX | P2 |

---

*Milestone M015 fechado. S01–S05 concluídas. Pronto para archivamento.*
