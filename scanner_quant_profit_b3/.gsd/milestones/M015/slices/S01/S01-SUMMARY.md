---
id: S01
parent: M015
milestone: M015
provides:
  - (none)
requires:
  []
affects:
  []
key_files:
  - docs/m015_traceability_audit_20260524.csv (64 linhas, 19.926 bytes)
  - docs/m015_traceability_audit_README.md (9.746 bytes)
key_decisions: []
patterns_established:
  - (none)
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-05-24T23:48:16.743Z
blocker_discovered: false
---

# S01: Data Source Traceability Audit

**S01 completa: 63 tickers auditados, 4 gap types identificados, root cause classification, CSV + README entregues.**

## What Happened

S01 executou auditoria completa de rastreabilidade de dados para 63 tickers do universo filtrado. O universo de 63 vem do data_source_traceability — não existe tabela de 'tickers filtrados' no scanner_quant.db. VALE3 foi auditado separadamente por não estar no traceability.

Investigação dos gaps:
- ri_documents vazio para 58/63: o CVM connector executou mas não inseriu docs — pipeline quebrou no step de INSERT
- market_type do cotahist_daily = '010' (não 'VISTA'): todas as consultas com filtro 'VISTA' retornavam 0, corrigido
- AI entries existentes (7 tickers): todas com NULL em company_name, sector, market_price — geradas por scanner técnico, não por ingestion fundamental
- 5 tickers com ri_documents: BBAS3, BBDC4, ITUB4, PETR4, WEGE3 — vieram de releases_connector/test, não do cvm_connector padrão
- 6 BDRs (ALUP11, BPAC11, KLBN11, SANB11, SAPR11, TAEE11): não suportados pelo CVM connector brasileiro
- VALE3: fora do universo de 63, cotahist=845, AI entry existe, mas nunca foi indexado pelo CVM connector

Correção de bug de schema: cotahist_daily market_type = '010' para ações à vista. Isso afeta TODO o codebase se houver outras consultas usando 'VISTA'.

## Verification

CSV com 64 linhas verificado via `wc -l`. README com 9.746 bytes verificado via `ls -la`. Contagens do DB verificadas: 63 traceability tickers, 5 com ri_documents, 7 com AI entries. Gap breakdown e root cause classification completos para todos os 63 tickers. 4 casos críticos investigados e documentados.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

Base de auditoria é 63 tickers (data_source_traceability), não 64. VALE3 auditado separadamente — tem cotahist=845 e AI entry=1 mas não tem traceability e não participated in the last data source audit. Market_type do cotahist_daily é '010', não 'VISTA' — todas as consultas iniciais retornaram 0, corrigido.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

None.
