# S01 — Auditoria de Cobertura de Valuation

## One-liner
Auditoria de cobertura para 9 tickers da watchlist: 4 com fair_value (mas 0% com valuation_method e FQS), 4 tickers sem CVM docs, 3 com discrepância entre traceability e dados reais.

## Narrativa

Executou-se uma varredura completa do estado de dados fundamentalistas para os 9 tickers da watchlist (`BBAS3`, `BBDC4`, `BPAC11`, `ITUB4`, `PETR4`, `SANB11`, `SUZB3`, `VALE3`, `WEGE3`) nos databases `data/database/scanner_quant.db` (principal, 9.5M rows em cotahist), `scanner_quant.db` (vazio) e `data/quant.db` (vazio). O audit leu apenas — nenhuma alteração, mock, ou cálculo pesado.

**Principais achados:**

- Cotahist completo para todos os 9 tickers (845 linhas cada, jan/2023–mai/2026) — source de mercado intacta.
- `asset_intelligence_snapshots` contém 7 tickers (BPAC11 e SANB11 ausentes). Todos os 7 têm `company_name=NULL`, `sector=NULL`, `market_price=NULL` — pipeline não popula nenhum campo cadastral. `valuation_method` é NULL em 100%. `fundamental_quality_score` é NULL em 100%.
- Fair values existem no banco para BBAS3 (64.84), ITUB4 (73.69), PETR4 (81.12), WEGE3 (40.16) — outputs reais preservados.
- Discrepância crítica: BPAC11, SANB11 e SUZB3 mostram 6.100 registros em `data_source_traceability` (REGULATORY) mas 0 em `ri_documents` — falha entre coleta e inserção no banco.
- VALE3 é o caso mais grave: sem traceabilidade, sem CVM docs, sem AI entry, sem valuation — precisa de ingestion completa.
- SUZB3 tem AI entry com `valuation_available=0` — pipeline marcou como sem valuation.

## Key Files
- `docs/coverage_audit_20260523.csv` — 37 colunas, 9 linhas (audit data)
- `docs/coverage_audit_README.md` — documentação completa de colunas, gaps, NULL semantics

## Key Decisions
- Metodologia setorial inferida da watchlist (não do banco): COSIF_BANK para bancos, COMMODITY_DCF para commodities, ENERGY_DCF para energia, INDUSTRIAL_DCF para industriais.
- Market price source-of-truth = cotahist (não AI), já que AI.market_price é NULL para todos.
- Discrepância CVM detectada via JOIN entre `data_source_traceability` e `ri_documents`.