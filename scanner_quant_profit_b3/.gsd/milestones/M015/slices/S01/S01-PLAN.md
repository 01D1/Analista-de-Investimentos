# S01: Data Source Traceability Audit

**Goal:** Auditar relação entre data_source_traceability, ri_documents, data_file_manifest, cotahist_daily e asset_intelligence_snapshots para os 63 tickers do universo filtrado. Identificar gaps, classificar root causes, gerar CSV e README.
**Demo:** After S01: Relatório de gap de 64 tickers — quais têm traceability mas sem ri_documents, categorizados por fonte (BDR, falha de pipeline, dados corrompidos)

## Must-Haves

- Complete the planned slice outcomes.

## Verification

- Run the task and slice verification checks for this slice.

## Tasks

- [x] **T01: Data Source Traceability Audit** `est:2h`
  1. Consultar scanner_quant.db para 63 tickers de data_source_traceability.
  2. Para cada ticker: traceability_count, ri_docs_count, data_file_manifest_count, ai_entry, cotahist (market_type=010), latest_price_date, latest_close, company_name, sector.
  3. Identificar: TRACE_NO_RI, MANIFEST_NO_RI, COTAHIST_NO_AI, RI_NO_SECTOR, AI_MISSING_METADATA, BDR_UNSUPPORTED.
  4. Investigar VALE3, SUZB3, SANB11, BPAC11.
  5. Classificar root cause: BDR/unsupported, CVM broken, not inserted, no AI entry, stale data.
  6. Gerar docs/m015_traceability_audit_20260524.csv.
  7. Gerar docs/m015_traceability_audit_README.md.
  8. Não alterar banco, não executar ingestion, não calcular valuation.
  - Files: `data/database/scanner_quant.db`, `scanner_quant.db`
  - Verify: CSV gerado com 63+1 linhas (header + 63 tickers), README com gap breakdown, root cause analysis e recomendações.

## Files Likely Touched

- data/database/scanner_quant.db
- scanner_quant.db
