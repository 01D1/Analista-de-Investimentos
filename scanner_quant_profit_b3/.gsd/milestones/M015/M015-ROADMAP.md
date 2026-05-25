# M015: CVM RI Ingestion and Sector Metadata Recovery

**Vision:** Resolver o principal gargalo identificado no M014: 29 tickers em NEEDS_CVM_DATA, 5 em NEEDS_SECTOR, 0 ELIGIBLE_NOW. O M015 recupera e padroniza dados reais de CVM/RI, cria/atualiza AI entries, e-popula metadados essenciais (company_name, sector, market_price, ri_docs_count) — sem calcular valuation pesado. Prepara a base para M016 Valuation Engine real.

## Success Criteria

- S01: 63 tickers auditados com gap breakdown categorizado ✅
- S01.5: Diagnóstico de premissas: roadmap corrigido, market_type catalogado, CVM connector diagnosticado, tickers classificados
- S03: AI entry coverage: 7/64 → ≥64/64 (incluindo VALE3 como caso manual/from-scratch); company_name+sector+market_price populados; sector='UNKNOWN' é placeholder técnico — não desbloqueia router, não permite valuation, ticker permanece NEEDS_SECTOR até haver fonte setorial rastreável
- S02: CVM connector funcional ou fallback documentado; ri_documents inseridos
- S04: Coverage audit antes/depois gerado; 0 ELIGIBLE_NOW → ≥1 ELIGIBLE_NOW
- S05: Router smoke test passando para 5 tickers; M016 ready
- Nenhum dado mockado criado
- D077-D082 preservado — stores não calculam valuation
- Fair values PETR4/BBAS3/ITUB4/WEGE3 não sobrescritos

## Slices

- [x] **S01: Data Source Traceability Audit** `risk:medium` `depends:[]`
  > After this: Relatório de gap de 63 tickers — 57 COTAHIST_NO_AI, 58 TRACE_NO_RI, 56 MANIFEST_NO_RI, 6 AI_MISSING_METADATA, 5 RI_NO_SECTOR. Bug de schema market_type='010' descoberto.

- [x] **S01.5: Connector and Schema Assumption Diagnosis** `risk:low` `depends:[S01]`
  > After this: Roadmap corrigido com nova ordem, bug market_type catalogado, diagnóstico do INSERT quebrado, classificação de 64+1 tickers, recomendação S03→S02.

- [x] **S03: AI Entry Creation and Metadata Population** `risk:medium` `depends:[S01.5]`
  > After this: AI entries mínimas criadas para 57 tickers (company_name do cotahist, market_price do cotahist, sector='UNKNOWN' como placeholder técnico). VALE3 criado manualmente/from-scratch. SUZB3 reclassificado. BDRs marcados como BDR_FII.
  > **Restrição sector='UNKNOWN':** usado apenas para garantir row existente na tabela; não desbloqueia router; não permite valuation; ticker permanece classificado como NEEDS_SECTOR até haver fonte setorial rastreável (CVM, RI, ou curadoria manual).
  > **Resultado:** 64/64 — 57 INSERT + 7 UPDATE. Setor rastreável=31, UNKNOWN=33, BDR_FII=6. fair_values PETR4/BBAS3/ITUB4/WEGE3 preservados. 0 erros. 8 tickers com preço stale (< 2026).

- [x] **S03.5: Corporate Actions / Ticker Alias Patch** `risk:low` `depends:[S03]`
  > After this: PETZ3 marcado LEGACY_TICKER (router bloqueado); AUAU3 com sector correto e AI entry; `config/ticker_aliases.yaml` criado; `src/utils/ticker_aliases.py` criado; `CoverageStatus.LEGACY_TICKER` adicionado; S04 AUTORIZADO.
  > **Data confirmada B3:** AUAU3 estreou 2026-01-05 (fusão concluída 2026-01-02).
  > Ver: `docs/m015_s035_corporate_action_patch_report.md`

- [ ] **S02: CVM RI Ingestion/INSERT Repair** `risk:high` `depends:[S01.5]`
  > After this: 58 tickers sem ri_documents classificados — alguns转入NEEDS_SECTOR, alguns转入PARTIAL/ELIGIBLE. VALE3 tratado manualmente. BDRs separados.

- [ ] **S04: Coverage Audit Before/After Report** `risk:low` `depends:[S03]`
  > After this: coverage_audit atualizado mostra antes/depois — 0 ELIGIBLE_NOW → ≥1 ELIGIBLE_NOW
  >
  > **Ajuste registrado (2026-05-24) — Corporate Action PETZ3 → AUAU3:**
  > Fusão Petz + Cobasi confirmada. PETZ3 marcado como LEGACY_TICKER (active=false, successor=AUAU3).
  > AUAU3 (União Pet Participações) adicionado como ticker ativo. Arquivos alterados:
  > `config/tickers.yaml`, `config/corporate_identity.yaml`, `config/cvm_codes.yaml`.
  > Database: 0 rows de PETZ3 — sem alteração necessária.
  > Ver: `docs/m015_s04_corporate_action_petz3_auau3.md`

- [ ] **S05: M016 Readiness Assessment** `[sketch]` `risk:low` `depends:[S04]`
  > After this: M016 pode rodar — router tem sector + market_price + ri_docs_count para todos os candidatos

## Key Risks

| Risk | Why It Matters |
|------|---------------|
| CVM connector data source offline | DEFAULT_ROOT=`12_PYTHON/pipeline...` não existe no ambiente atual; 58 tickers ficam sem RI mesmo após S02 |
| BDRs need separate source | 6 BDRs não são cobertos pelo CVM connector; sem source alternativa, sempre retornam 0 |
| VALE3 manual indexing | VALE3 não está no universo CVM; precisa de indexação manual ou não será coberto |
| market_type='VISTA' filters silently fail | Qualquer código usando `market_type='VISTA'` retorna 0 linhas sem erro — silently corrupted |
| AI metadata NULL despite RI docs | 5 tickers têm ri_documents mas AI entries com NULL em company_name/sector/market_price |

## Proof Strategy

| Retire in | Risk or Unknown | What Will Be Proven |
|-----------|-----------------|-------------------|
| S03 | AI_ENTRY_NOT_CREATED para 57 tickers | Após S03: `SELECT COUNT(*) FROM asset_intelligence_snapshots WHERE sector IS NOT NULL` ≥ 63 |
| S02 | CVM connector não insere ri_documents | Após S02: `SELECT COUNT(*) FROM ri_documents WHERE ticker IN (...) AND source='cvm_connector'` ≥ 100 |
| S04 | 0 ELIGIBLE_NOW | Após S04: router retorna ≥1 ELIGIBLE_NOW para os 63 tickers |
| S05 | M016 não é executável | Após S05: smoke test passa para ≥5 tickers, M016 ready=true |

## Schema Bug: market_type

- cotahist_daily.market_type = `'010'` para ações à vista — **não** `'VISTA'`
- Qualquer filtro `market_type='VISTA'` retorna 0 linhas sem erro
- Arquivos que usam `'010'` (correto): todos os arquivos em src/quant/, src/options/, src/data_quality/, src/scanners/
- Arquivos que **não usam** 'VISTA': nenhum encontrado (o bug foi detectado antes de ser introduzido em novos arquivos)
- Ação: catalogar apenas, não alterar código ainda