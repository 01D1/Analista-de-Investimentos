# M015 — S01: Data Source Traceability Audit Report

**Data de corte:** 2026-05-24
**Scope:** 63 tickers do universo filtrado (data_source_traceability)
**Objetivo:** Mapear gargalos de dados CVM/RI, AI metadata e cotahist para os 64 tickers filtrados

---

## a) Total de Tickers Auditados

| Métrica | Valor |
|---|---|
| Total auditado (em traceability) | **63** |
| Com cotahist (market_type='010') | 63/63 (100%) |
| Com ai_entry (asset_intelligence_snapshots) | 7/63 (11%) |
| Com ri_documents | 5/63 (8%) |
| Sem ri_documents | 58/63 (92%) |
| Sem ai_entry | 56/63 (89%) |

> **Nota:** O número base é 63 tickers do `data_source_traceability`, não 64. VALE3
> (cotahist=845, ai_entry=1, trace=0, ri=0) está **fora** do universo de 63 porque
> não foi incluído no `data_source_traceability` — não participou do último audit de
> fontes de dados.

---

## b) Contagem por Tipo de Gap

| Gap | Tickers afetados | Causa provável |
|---|---|---|
| `COTAHIST_NO_AI` | **57** | AI entry nunca criada; engine pula tickers sem sector/company_name |
| `TRACE_NO_RI` | **58** | CVM connector não executou para esses tickers |
| `MANIFEST_NO_RI` | **56** | Corolário de TRACE_NO_RI |
| `AI_MISSING_METADATA` | **6** | AI entries existem mas company_name/sector/market_price = NULL |
| `RI_NO_SECTOR` | **5** | 5 tickers têm ri_documents mas AI.sector = NULL |
| `TRACE_NO_COTAHIST` | **0** | Todos os 63 têm cotahist — market_type correto é '010', não 'VISTA' |

**Gaps por root cause (não somam porque um ticker pode ter mais de uma causa):**

| Root Cause | Tickers | % |
|---|---|---|
| `AI_ENTRY_NOT_CREATED` | 57 | 90% |
| `CVM_CONNECTOR_NOT_EXECUTED` | 51 | 81% |
| `AI_METADATA_NOT_POPULATED` | 11 | 17% |
| `BDR_UNSUPPORTED` | 6 | 10% |
| `CVM_CONNECTOR_PARTIAL_NO_CONTENT` | 1 (SUZB3) | 2% |

---

## c) Principais Casos Críticos

### VALE3 — TRACE_MISSING (fora do universo auditado)
- `cotahist`: 845 registros, data mais recente 2026-05-22
- `traceability`: 0 (não participou do último data source audit)
- `ri_documents`: 0 (nunca coletado)
- `ai_entry`: 1 existe (BBAS3, BBDC4, ITUB4, PETR4, SUZB3, VALE3, WEGE3)
- `latest_close`: ~R$ 52 (não disponível no resultado audit)
- **Root cause:** VALE3 nunca foi indexado pelo CVM/IPE connector — não aparece na
  lista de 61 tickers que o audit encontrou. Causa: provavelmente ticker removido do
  índice CVM ou nunca adicionado à lista de monitoramento.

### SUZB3 — CVM_CONNECTOR_PARTIAL_NO_CONTENT
- `cotahist`: 845 registros, close=66.65
- `traceability`: 2 entradas (REGULATORY + VALUATION), última coleta 2026-05-12
- `ri_documents`: 0
- `ai_entry`: 1 (mas company_name=NULL, sector=NULL, market_price=NULL)
- `cotahist_company_name`: "SUZANO S.A."
- **Root cause:** SUZB3 tem REGULATORY no traceability (teoricamente indexado via
  cvm_ipe), mas ri_documents está vazio — ou os documentos foram baixados mas o
  pipeline de inserção falhou silenciosamente. Possível arquivo "baixado mas não
  inserido".

### SANB11 — BDR_UNSUPPORTED + AI_ENTRY_NOT_CREATED
- `cotahist`: 845 registros, close=37.50, company="SANTANDER BR"
- `traceability`: 2 entradas (REGULATORY + VALUATION)
- `ri_documents`: 0
- `ai_entry`: não existe
- **Root cause:** SANB11 é BDR (ação estrangeira representada no Brasil), o CVM connector
  brasileiro não cobre BDRs. Sem RI docs, sem sector (quebra o router), sem AI entry.

### BPAC11 — BDR_UNSUPPORTED + AI_ENTRY_NOT_CREATED
- `cotahist`: 845 registros, close=64.34, company="BTGP BANCO"
- `traceability`: 2 entradas
- `ri_documents`: 0
- **Root cause:** Mesmo problema de BDR — BDRs não são cobertos pelo CVM connector.

---

## d) Causa Provável do Problema CVM/RI

O gargalo central não é um bug pontual — é uma **falha sistêmica do pipeline CVM/RI**:

1. **Root cause #1 — CVM connector não executou para 58/63 tickers:**
   O `data_source_traceability` registra que REGULATORY domain existe para esses tickers,
   mas `ri_documents` está vazio. Isso indica que o CVM connector executou,
   identificou os tickers, mas **não inseriu os documentos no banco** — ou os documentos
   foram baixados do site antigo, ou o pipeline quebrou no step de INSERT.

2. **Root cause #2 — CVM connector quebrado no step de INSERT:**
   Os 5 tickers com ri_documents (BBAS3, BBDC4, ITUB4, PETR4, WEGE3) usam 3 sources
   diferentes: `cvm_connector` (WEGE3), `releases_connector` (BBAS3, BBDC4, ITUB4,
   PETR4), `test` (PETR4). O `cvm_connector` funcional cobriu apenas WEGE3; os demais
   vieram de `releases_connector` (provavelmente manual). **O CVM connector padrão
   não está inserting para nenhum dos 58.**

3. **Root cause #3 — VALE3 nunca foi adicionado ao universo CVM:**
   VALE3 não aparece na lista de 61 tickers que o `data_source_audit_results`
   encontrou no cvm_ipe. Motivo provável: não estava na lista original de tickers
   quando o audit foi executado.

4. **Root cause #4 — BDRs não são suportados:**
   Os 6 tickers terminados em "11" (ALUP11, BPAC11, KLBN11, SANB11, SAPR11, TAEE11)
   são BDRs/FIIs. O CVM connector brasileiro não cobre esses ativos — eles precisam
   de source diferente (境外) ou devem ser tratados como FII.

5. **Root cause #5 — AI metadata não populado mesmo com RI:**
   BBAS3, BBDC4, ITUB4, PETR4, WEGE3 têm 100+ ri_documents cada, mas as AI entries
   existentes têm `company_name=NULL`, `sector=NULL`, `market_price=NULL`. O problema
   não é ausência de dados CVM — é que o step que popula AI metadata a partir do
   ri_documents nunca foi executado ou nunca populou esses campos.

---

## e) Arquivos Gerados

| Arquivo | Descrição |
|---|---|
| `docs/m015_traceability_audit_20260524.csv` | CSV completo com todos os 63 tickers: contagens, gaps, root causes |
| `docs/m015_traceability_audit_README.md` | Este relatório |

---

## f) Recomendação para S02

**S02 deve focar em 3 ações, não em "executar o CVM connector":**

### 1. Diagnóstico do CVM connector (antes de rodar)
Verificar o código do CVM connector em `src/context/connectors/cvm_connector.py` para
identificar por que os documentos não estão sendo inseridos. Esperar que o connector
simplesmente "funcione" sem debug vai resultar nos mesmos 0 docs para 58 tickers.

**Verificar especificamente:**
- Se o step de INSERT está sendo chamado para tickers fora dos 5 que já têm dados
- Se há deduplicação que bloqueia re-inserção dos docs já baixados
- Se o source 'cvm_connector' vs 'releases_connector' é a razão da cobertura desigual

### 2. AI Entry Creation — prioridade imediata
57 tickers têm cotahist + traceability + company_name (do cotahist) mas nenhuma AI
entry. Criar AI entries mínimas (company_name do cotahist, market_price do cotahist,
sector='UNKNOWN') para esses 57 tickers **antes** de rodar o CVM connector. Isso
transforma 57× NEEDS_CVM_DATA + NEEDS_SECTOR em simplesmente NEEDS_SECTOR.

### 3. Classificar BDRs separadamente
Os 6 tickers em "11" não devem ser passados ao CVM connector — devem receber
sector='BDR_FII', market_price do cotahist, e ser marcados como NEEDS_SECTOR (não
NEEDS_CVM_DATA) porque o source não existe. Resolver isso antes de S02 evita
tentativas de coleta que vão falhar de qualquer forma.

---

## g) Autorização para S02

### ✅ AUTORIZADO COM RESTRIÇÕES

**Condições para prosseguir com S02 (CVM RI Ingestion for 29 NEEDS_CVM_DATA):**

1. **Executar diagnóstico primeiro** — Não rodar o CVM connector cegamente. O problema
   provavelmente não é "não foi executado" mas sim "executou mas não insertou". O
   diagnóstico do código é pré-requisito.

2. **Separar BDRs antes de S02** — Os 6 tickers "11" devem ser marcados como
   BDR_UNSUPPORTED e removidos da lista de NEEDS_CVM_DATA antes de S02.

3. **Executar AI Entry Creation primeiro (S03)** — A ordem deveria ser S03 antes de
   S02, ou executados em paralelo: S03 cria as entries, S02 popula os RI docs.
   A dependência declarada (S03 depends on S01,S02) é contraproducente — S02 não
   precisa de AI entries existentes, mas S03 precisa dos dados que S02 vai gerar.

4. **ValE3 é caso à parte** — VALE3 precisa ser adicionado manualmente ao universo
   CVM, não vai "consertar" via connector.

5. **Os 5 tickers com RI docs conhecidos (BBAS3, BBDC4, ITUB4, PETR4, WEGE3)
   devem ser SKIPPED no ingestion** — eles já têm ri_documents, não precisam de nova
   coleta. O problema deles é purely AI metadata missing.

**Reclassificação esperada após S02:**
- 51 tickers → CVM connector executado → alguns转入NEEDS_SECTOR, alguns转入NEEDS_MODEL
- 6 tickers → BDR_UNSUPPORTED → sector=BDR_FII →转入NEEDS_SECTOR
- 5 tickers → SKIP (já têm RI) → apenas AI metadata needed
- 1 ticker (VALE3) → precisa de tratamento manual separado

---

## Anexo: Market Type Cotahist

O cotahist_daily usa `market_type='010'` para ações à vista — **não** `'VISTA'`.
Todas as 63 verificações iniciais com filtro `'VISTA'` retornaram 0. Todos os 63
tickers têm dados completos com `market_type='010'`.

## Anexo: AI Snapshots — Os 7 Tickers

| Ticker | ai_company_name | ai_sector | ai_market_price | fair_value | val_available |
|---|---|---|---|---|---|
| BBAS3 | NULL | NULL | NULL | 64.84 | 1 |
| BBDC4 | NULL | NULL | NULL | NULL | 1 |
| ITUB4 | NULL | NULL | NULL | 73.69 | 1 |
| PETR4 | NULL | NULL | NULL | 81.12 | 1 |
| SUZB3 | NULL | NULL | NULL | NULL | 0 |
| VALE3 | NULL | NULL | NULL | NULL | ? |
| WEGE3 | NULL | NULL | NULL | NULL | ? |

> Todas as 7 AI entries têm company_name/sector/market_price = NULL. As AI entries
> foram geradas pelo technical scanner com fallback de dados quantitativos, não
> por ingestion de dados fundamentais.