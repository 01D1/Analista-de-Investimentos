---
estimated_steps: 8
estimated_files: 2
skills_used: []
---

# T01: Data Source Traceability Audit

1. Consultar scanner_quant.db para 63 tickers de data_source_traceability.
2. Para cada ticker: traceability_count, ri_docs_count, data_file_manifest_count, ai_entry, cotahist (market_type=010), latest_price_date, latest_close, company_name, sector.
3. Identificar: TRACE_NO_RI, MANIFEST_NO_RI, COTAHIST_NO_AI, RI_NO_SECTOR, AI_MISSING_METADATA, BDR_UNSUPPORTED.
4. Investigar VALE3, SUZB3, SANB11, BPAC11.
5. Classificar root cause: BDR/unsupported, CVM broken, not inserted, no AI entry, stale data.
6. Gerar docs/m015_traceability_audit_20260524.csv.
7. Gerar docs/m015_traceability_audit_README.md.
8. Não alterar banco, não executar ingestion, não calcular valuation.

## Inputs

- None specified.

## Expected Output

- `docs/m015_traceability_audit_20260524.csv`
- `docs/m015_traceability_audit_README.md`

## Verification

CSV gerado com 63+1 linhas (header + 63 tickers), README com gap breakdown, root cause analysis e recomendações.
