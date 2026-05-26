# M017 — Structured DFP/ITR Financial Statements Parser

**Versão:** 1.0.0  
**Data:** 2026-05-26  
**Status:** ✅ FECHADO — administrativamente em 2026-05-26  
**Depends on:** M016 ✅ CLOSED (2026-05-25)  
**Predecessor gap:** D110 — 18 tickers NEEDS_FINANCIALS com modelos prontos, aguardando parsing DFP/ITR

---

## Vision

Alimentar os 18 modelos de valuation criados no M016 com dados financeiros reais extraídos
de DFP/ITR/CVM. M017 não calcula fair_value — cria a infraestrutura de dados que permite
os modelos calcularem automaticamente assim que `valuation_financial_inputs` for populado.

**Princípio:** extrair apenas o que se pode auditar. Todo número tem fonte rastreável.
EBITDA sem DFP/ITR = dado inexistente, não estimativa.

---

## Contexto Herdado de M016

| Fato | Valor |
|------|-------|
| Tickers com fair_value auditável | 9 (PRESERVE_EXISTING) |
| Tickers NEEDS_FINANCIALS | 18 — modelos prontos, falta extração |
| Tickers TECH_FALLBACK | 1 (VIVT3) |
| Tickers NEEDS_DATA (ri_docs=0) | 1 (VALE3) |
| Tickers NEEDS_RI_DOCS | 2 (AUAU3, NTCO3) |
| LEGACY_TICKER permanente | 1 (PETZ3) |
| `b3_financials` table no DB | Não existe — a criar em S01 |
| `ri_documents.extracted_text` | Empty (0/3.251) — não é fonte viável |

### Por que 18 ficaram bloqueados em M016

Os 5 modelos setoriais (bank, commodity, utility, retail, industry) precisam de:
`ebitda`, `free_cash_flow`, `net_debt`, `shares_outstanding`.

Esses campos existem nos DFP/ITR das empresas, mas **não foram parseados para estrutura
consultável**. M017 implementa esse parsing. Quando concluído, os modelos calculam
automaticamente sem alteração de código de valuation.

---

## Universo de Tickers M017

### 18 NEEDS_FINANCIALS — distribuição por modelo e fonte disponível

| Modelo | Ticker | Excel Pipeline | CVM CSV | Status |
|--------|--------|:--------------:|:-------:|--------|
| UTILITY | EGIE3 | ✅ | ✅ | Track A + B |
| UTILITY | SBSP3 | ✅ | ✅ | Track A + B |
| UTILITY | TAEE11 | ✅ | ✅ | Track A + B |
| RETAIL | AZZA3 | ✅ | ✅ | Track A + B |
| RETAIL | LREN3 | ✅ | ✅ | Track A + B |
| RETAIL | MGLU3 | ✅ | ✅ | Track A + B |
| RETAIL | PCAR3 | ✅ | ✅ | Track A + B |
| RETAIL | VIVA3 | ✅ | ✅ | Track A + B |
| INDUSTRY | RADL3 | ✅ | ✅ | Track A + B |
| COMMODITY | PRIO3 | ❌ | ✅ | Track B only |
| COMMODITY | RECV3 | ❌ | ✅ | Track B only |
| INDUSTRY | FLRY3 | ❌ | ✅ | Track B only |
| INDUSTRY | HYPE3 | ❌ | ✅ | Track B only |
| INDUSTRY | KLBN11 | ❌ | ✅ | Track B only |
| INDUSTRY | RAIL3 | ❌ | ✅ | Track B only |
| INDUSTRY | RENT3 | ❌ | ✅ | Track B only |
| INDUSTRY | SUZB3 | ❌ | ✅ | Track B only |
| INDUSTRY | VAMO3 | ❌ | ❌ | MANUAL_REVIEW |

> **VAMO3:** 0 xlsx + 0 CSVs CVM disponíveis → permanece NEEDS_FINANCIALS ao final do M017.
> Requer investigação de fonte alternativa (RI manual, API B3, CVM direto).

### Tickers fora de escopo M017

| Status | Tickers | Motivo |
|--------|---------|--------|
| PRESERVE_EXISTING | ABCB4, BBAS3, BBDC4, BPAC11, BRSR6, ITUB4, SANB11, PETR4, WEGE3 | fair_value auditável — não alterar |
| NEEDS_DATA | VALE3 | ri_docs=0 — aguarda CVM ingestion (SXX) |
| NEEDS_RI_DOCS | AUAU3, NTCO3 | sem RI docs — aguarda CVM |
| LEGACY_TICKER | PETZ3 | Extinto — **permanentemente bloqueado** |
| TECH_FALLBACK | VIVT3 | Modelo disponível; entrar só se CVM CSV cobrir inputs |

---

## Arquitetura de Dados — Two-Track

A auditoria de fontes revelou dois caminhos para popular `valuation_financial_inputs`:

### Track A — Excel Pipeline Bridge (9 tickers, rota rápida)

**Fonte:** `12_PYTHON/pipeline banco completo/outputs/Valuation_*.xlsx`  
**Tickers elegíveis:** EGIE3, SBSP3, TAEE11, AZZA3, LREN3, MGLU3, PCAR3, VIVA3, RADL3  
**Campos disponíveis:** DRE, DCF, Balanço — extraíveis das sheets existentes  
**Precedência:** suplementar; CVM CSV é autoridade quando ambos disponíveis

```
Valuation_EGIE3.xlsx
├── Sheet "DRE"        → ebitda, receita_liquida
├── Sheet "DCF"        → free_cash_flow, wacc, g
├── Sheet "Balanço"    → net_debt, shares_outstanding
└── Sheet "Resumo"     → fair_value (não usar — apenas conferência)
```

> A função `_extract_fair_value_from_excel()` já existe em `bank_model.py` e pode
> ser generalizada para extrair campos financeiros das mesmas planilhas.

### Track B — CVM CSV (17 tickers, rota completa)

**Fonte:** `12_PYTHON/data/raw/cvm/2025/{TICKER}_{DFP|ITR}_{statement}_{year}.csv`  
**Tickers elegíveis:** todos exceto VAMO3  
**Autoridade:** fonte primária (CVM oficial)

```
Tipos de demonstração disponíveis (por ticker):
  {TICKER}_DFP_BPA_{year}.csv   → Balanço Patrimonial Ativo
  {TICKER}_DFP_BPP_{year}.csv   → Balanço Patrimonial Passivo
  {TICKER}_DFP_DRE_{year}.csv   → Demonstração do Resultado
  {TICKER}_DFP_DFC_{year}.csv   → Demonstração do Fluxo de Caixa
  {TICKER}_ITR_BPA_{year}.csv   → Idem (trimestral)
  {TICKER}_ITR_BPP_{year}.csv
  {TICKER}_ITR_DRE_{year}.csv
  {TICKER}_ITR_DFC_{year}.csv
  + outros (DRA, DVA, DMPL conforme disponibilidade)
```

**Parser existente:** `12_PYTHON/src/parsers/dfp_parser.py` — a auditar em S02.

### Tabela destino — `valuation_financial_inputs`

```sql
CREATE TABLE valuation_financial_inputs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    period_type     TEXT NOT NULL,   -- 'DFP' | 'ITR'
    reference_date  DATE NOT NULL,   -- data de referência da demonstração
    fiscal_year     INTEGER NOT NULL,
    -- Métricas extraídas
    ebitda          REAL,
    ebit            REAL,
    receita_liquida REAL,
    free_cash_flow  REAL,
    capex           REAL,
    net_debt        REAL,
    debt_gross      REAL,
    cash            REAL,
    shares_outstanding REAL,
    roe             REAL,
    -- Auditabilidade
    source_track    TEXT NOT NULL,   -- 'CVM_CSV' | 'EXCEL_PIPELINE'
    source_file     TEXT NOT NULL,   -- caminho do arquivo fonte
    extracted_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    input_hash      TEXT NOT NULL,   -- hash de (ticker, period_type, reference_date, source_file)
    extraction_notes TEXT,           -- warnings, substituições, flags
    UNIQUE(ticker, period_type, reference_date, source_track)
);
```

---

## Slices — Visão Geral

| # | Slice | Prioridade | Depende | Status |
|---|-------|:-----------:|---------|--------|
| **S01** | Schema Design — `valuation_financial_inputs` | **P0 BLOQUEADOR** | — | ✅ |
| **S02** | DFP/ITR Parser Audit — mapear cobertura por fonte | P1 | S01 | ✅ |
| **S02.5** | CVM Full Dataset Localizer / Downloader | **P0 DESBLOQUEADOR** | S02 | ⬜ |
| **S03** | Metric Extraction Engine — extrair 9 campos por ticker | P1 | S02.5 | ⬜ |
| **S04** | Populate Financial Inputs — inserir no DB | P2 | S03 | ⬜ |
| **S05** | Model Re-run Readiness — validar que modelos lêem novos dados | P2 | S04 | ⬜ |
| **SXX** | CVM Ingestion VALE3 / NTCO3 / AUAU3 (paralelo) | P3 | — | ⬜ |

> S01 **bloqueia** S02–S05. S02.5 **desbloqueada após S02** — resolve arquivos cloud-only antes que S03 execute qualquer parsing. SXX é paralelo e não bloqueia nada.

---

## S01 — Schema Design (P0 BLOQUEADOR)

### Objetivo
Criar a tabela `valuation_financial_inputs` no banco canônico `scanner_quant.db`.
Definir o schema completo antes de qualquer extração para garantir consistência de tipos
e rastreabilidade de fonte.

### Escopo
- **Criar:** migration SQL para `valuation_financial_inputs` (schema acima)
- **Criar:** `src/parsers/financial_inputs_store.py` — CRUD functions para a tabela
- **Verificar:** integridade de `scanner_quant.db` e que nenhuma tabela homônima existe
- **Documentar:** mapeamento campo → coluna DFP/ITR (conta CVM → campo normalizado)

### O que NÃO faz
- Não insere dados
- Não altera tabelas existentes (`ri_documents`, `asset_intelligence_snapshots`, `cotahist_daily`)
- Não calcula valuation
- Não cria mocks

### Mapeamento de contas CVM → campos

| Campo destino | Conta DRE/BPA/DFC (CVM) | Observação |
|--------------|------------------------|------------|
| `ebitda` | EBIT + D&A (DRE) OU linha direta se disponível | Calcular a partir de EBIT quando não há linha direta |
| `ebit` | "Resultado antes do resultado financeiro" (DRE) | Linha padrão CVM |
| `receita_liquida` | "Receita de Venda de Bens e/ou Serviços" (DRE) | Linha raiz DRE |
| `free_cash_flow` | "Fluxo de caixa das atividades operacionais" (DFC) − Capex | DFC direto ou indireto |
| `capex` | "Aquisição de ativo imobilizado" (DFC atividades investimento) | Negativo no DFC → usar valor absoluto |
| `net_debt` | `debt_gross − cash` | Calculado |
| `debt_gross` | "Empréstimos e Financiamentos" circulante + não-circulante (BPP) | Somar ambos horizontes |
| `cash` | "Caixa e equivalentes de caixa" (BPA) | Linha raiz BPA |
| `shares_outstanding` | Não vem do DFP — fonte B3/CVM notas explicativas | Fallback: `cotahist_daily` última data |

### Critérios de Aceite (S01-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | Tabela `valuation_financial_inputs` criada no DB | `SELECT name FROM sqlite_master WHERE type='table'` |
| AC-02 | Constraint `UNIQUE(ticker, period_type, reference_date, source_track)` ativa | INSERT duplicado → IntegrityError |
| AC-03 | `financial_inputs_store.py` com funções `upsert_inputs()`, `get_inputs(ticker)`, `list_covered_tickers()` | teste unitário |
| AC-04 | Nenhuma tabela existente alterada | diff schema antes/depois |
| AC-05 | Mapeamento conta CVM → campo documentado (arquivo `docs/M017_CVM_FIELD_MAPPING.md`) | arquivo criado |
| AC-06 | Banco não corrompido após migration | `PRAGMA integrity_check` |

### Riscos S01

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Schema incompleto — falta campo necessário para algum modelo | Média | Alto | Revisar todos os inputs de bank/commodity/utility/retail/industry antes de finalizar schema |
| Migration irreversível corrompendo DB | Baixa | Crítico | Backup de `scanner_quant.db` antes de migration; transação atômica |
| `shares_outstanding` não disponível via DFP/ITR | Alta | Alto | Fallback para `cotahist_daily`; documentar como `source_track=B3_MARKET_DATA`; penalizar confidence |

---

## S02 — DFP/ITR Parser Audit

### Objetivo
Auditar o `dfp_parser.py` existente em `12_PYTHON/src/parsers/` e mapear precisamente
quais contas CVM estão disponíveis nos CSVs de cada ticker. Produzir um mapa de cobertura
antes de qualquer extração para evitar surpresas.

### Escopo
- **Auditar:** `12_PYTHON/src/parsers/dfp_parser.py` — o que já extrai, o que falta
- **Mapear:** para cada um dos 17 tickers com CVM CSV, quais arquivos existem
- **Verificar:** se os CSVs contêm as contas mapeadas em S01 (DRE, DFC, BPA, BPP)
- **Identificar:** lacunas por ticker (conta ausente, valor zerado, data desatualizada)
- **Documentar:** relatório `docs/M017_S02_PARSER_AUDIT.md` com cobertura por ticker/campo

### O que NÃO faz
- Não altera o dfp_parser.py sem primeiro auditar
- Não insere dados no banco
- Não calcula valuation

### Artefatos a inspecionar

```
12_PYTHON/src/parsers/dfp_parser.py              ← parser existente a auditar
12_PYTHON/data/raw/cvm/2025/                     ← 17 tickers × ~10 CSVs cada
12_PYTHON/data/processed/{TICKER}/dfp_{year}.json ← JSONs pré-processados (parcial)
```

### Critérios de Aceite (S02-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `dfp_parser.py` lido e documentado: inputs, outputs, limitações | seção no relatório |
| AC-02 | Cobertura mapeada para os 17 tickers com CSV | tabela ticker × campo × disponível/ausente |
| AC-03 | CSVs amostrados: pelo menos 1 linha de DRE, DFC, BPA, BPP verificada por ticker | evidência no relatório |
| AC-04 | Campos ausentes por ticker explicitamente listados | lista de gaps |
| AC-05 | Decisão sobre reutilização vs reescrita do `dfp_parser.py` documentada | seção "Decisão de Implementação" |
| AC-06 | VAMO3 confirmado como sem fonte (0 CSVs) | evidência no relatório |
| AC-07 | Relatório `docs/M017_S02_PARSER_AUDIT.md` criado | arquivo presente |

### Riscos S02

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| dfp_parser.py usa estrutura incompatível com scanner_quant | Média | Médio | Adaptar wrapper; não reescrever do zero se funcional |
| CSVs CVM com encoding/formato inconsistente entre tickers | Alta | Médio | Detectar na auditoria; normalizar em S03 |
| Conta CVM com nome diferente entre empresas (ex: EBIT ≠ "Resultado antes do financeiro") | Alta | Alto | Mapear top-3 variações por campo; fallback hierárquico em S03 |
| JSONs pré-processados em `data/processed/` incompletos ou stale | Média | Baixo | Usar CSVs raw como fonte; JSONs são cache opcional |

---

## S02.5 — CVM Full Dataset Localizer / Downloader

### Contexto — Por que este slice existe

A S02 confirmou duas condições bloqueadoras para S03:

1. **Arquivos cloud-only**: `12_PYTHON/data/raw/cvm/2025/` vive no OneDrive. Arquivos com
   atributo `com.apple.metadata:kMDItemWhereFroms` ou sem conteúdo local (`xattr -p
   com.apple.quarantine`) são placeholders — abrir um placeholder dispara sync; ler em
   batch pelo Python falha silenciosamente com arquivo de 0 bytes ou abre conexão de rede
   não controlada.

2. **Demonstrações ausentes**: O dataset atual contém apenas `INDEX_DFP`, `INDEX_ITR`,
   `BPA_CON`, `BPA_IND`, `BPP_CON` e `BPP_IND`. Faltam `DRE_CON`, `DRE_IND`, `DFC_CON`,
   `DFC_IND`, `DVA_CON`, `DVA_IND`, `DMPL_CON` e `DMPL_IND` — sem os quais o extrator
   de S03 retorna `None` para `ebitda`, `ebit`, `free_cash_flow` e `capex` em todos os
   tickers.

S02.5 resolve **ambas** as condições antes que S03 seja executada — e constrói um dataset
CVM/DFP/ITR **amplo e reutilizável** para todo o projeto, não apenas para os 18 NEEDS_FINANCIALS.

### Objetivo

Baixar e materializar localmente os 12 tipos de demonstração (BPA, BPP, DRE, DFC, DVA,
DMPL — CON e IND) para **todos os tickers com CNPJ mapeado em `cvm_codes.yaml`**, construindo
um dataset CVM estrutural reutilizável para valuation, radar, coverage e expansões futuras.

**Prioridade de validação:** os 18 tickers NEEDS_FINANCIALS continuam sendo o grupo de
validação prioritária do M017 — eles desbloqueiam os modelos M016. O dataset amplo é o
objetivo estrutural; os 18 são a régua de aceite imediata.

### Escopo

- **Auditar:** detectar quais arquivos em `data/raw/cvm/2025/` são cloud-only (placeholder
  OneDrive) vs. realmente materializados localmente
- **Identificar:** quais dos 12 tipos de demonstração estão ausentes por ticker
- **Baixar:** diretamente do endpoint CVM (`dados.cvm.gov.br`) todos os arquivos faltantes
  para **todos os tickers com CNPJ mapeado** — execução em lotes/batches quando necessário
- **Verificar:** após download, cada arquivo é aberto e tem ≥ 1 linha de dados (não vazio)
- **Inventário amplo:** gerar tabela de cobertura por ticker, CNPJ e tipo de demonstração
- **Seção específica 18 NEEDS_FINANCIALS:** subseção dedicada no relatório com status
  detalhado dos tickers que desbloqueiam os modelos M016
- **Relatório:** `docs/M017_S02.5_DATASET_AUDIT.md` com status por ticker/tipo

### O que NÃO faz

- Não lê CSV inteiro no contexto — apenas `head()` de verificação (5 linhas)
- Não popula `valuation_financial_inputs`
- Não calcula valuation
- Não cria mocks
- Não altera fair values existentes
- Não altera opções/OOS/paper/scheduler

### Demonstrações alvo (12 tipos obrigatórios)

| Tipo | Demonstração | Necessária para |
|------|-------------|-----------------|
| `BPA_CON` | Balanço Patrimonial Ativo (Consolidado) | `cash`, `net_debt` (parcial) |
| `BPA_IND` | Balanço Patrimonial Ativo (Individual) | fallback se CON ausente |
| `BPP_CON` | Balanço Patrimonial Passivo (Consolidado) | `debt_gross`, `net_debt` |
| `BPP_IND` | Balanço Patrimonial Passivo (Individual) | fallback se CON ausente |
| `DRE_CON` | Demonstração do Resultado (Consolidado) | `ebitda`, `ebit`, `receita_liquida` |
| `DRE_IND` | Demonstração do Resultado (Individual) | fallback se CON ausente |
| `DFC_CON` | Demonstração do Fluxo de Caixa (Consolidado) | `free_cash_flow`, `capex` |
| `DFC_IND` | Demonstração do Fluxo de Caixa (Individual) | fallback se CON ausente |
| `DVA_CON` | Demonstração do Valor Adicionado (Consolidado) | suplementar |
| `DVA_IND` | Demonstração do Valor Adicionado (Individual) | suplementar |
| `DMPL_CON` | Demonstração das Mutações do PL (Consolidado) | suplementar |
| `DMPL_IND` | Demonstração das Mutações do PL (Individual) | suplementar |

> **Prioridade de download:** DRE e DFC são críticos (bloqueiam extração). BPA e BPP
> já existem — verificar se são locais. DVA e DMPL são suplementares — baixar se disponíveis.

### Estratégia de download — CVM direto

```
Endpoint CVM: https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/
Arquivos anuais: dfp_cia_aberta_{TIPO}_{ANO}.zip   (ex: dfp_cia_aberta_DRE_con_2024.zip)
Arquivos ITR:   https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/
               itr_cia_aberta_{TIPO}_{ANO}.zip

Fluxo:
  1. Carregar todos os tickers com CNPJ não-nulo de cvm_codes.yaml (~88 tickers)
  2. Para cada tipo em [DRE_CON, DRE_IND, DFC_CON, DFC_IND, DVA_CON, DVA_IND, DMPL_CON, DMPL_IND]:
       a. Baixar ZIP anual (DFP 2024 + ITR 2024 conforme disponível)
       b. Extrair CSV do ZIP usando chunksize (não carregar inteiro em memória)
       c. Filtrar apenas linhas dos tickers mapeados (por CD_CVM/CNPJ)
       d. Salvar CSV filtrado em data/raw/cvm/2025/{TICKER}_{DFP|ITR}_{TIPO}_{ANO}.csv
       e. Executar em lotes/batches para respeitar limites de memória e rede
  3. Para BPA/BPP já existentes: verificar se local ou cloud-only
       a. Se cloud-only → re-materializar (baixar da CVM diretamente — não depender de sync OneDrive)
       b. Se local → verificar integridade (não vazio, ≥ 1 linha dados)
  4. Gerar inventário completo: ticker × CNPJ × tipo × status (local/cloud-only/baixado/ausente)
  5. Gerar subseção específica para os 18 NEEDS_FINANCIALS com status detalhado
```

> **Tamanho estimado:** ZIPs CVM DFP DRE ≈ 5–15 MB cada. Filtragem para ~88 tickers
> produz CSVs de ≈ 100 KB–2 MB por tipo — totalmente manejável com chunksize.
>
> **Tickers excluídos do download:** AUAU3 (CNPJ nulo), PETZ3 (LEGACY_TICKER — excluir para
> evitar poluição; dados não serão usados). Todos os demais com CNPJ mapeado são incluídos.

### Artefatos esperados após S02.5

```
data/raw/cvm/2025/
├── {TICKER}_DFP_DRE_CON_2024.csv    ← novo (todos os tickers mapeados com CNPJ)
├── {TICKER}_DFP_DRE_IND_2024.csv    ← novo
├── {TICKER}_DFP_DFC_CON_2024.csv    ← novo
├── {TICKER}_DFP_DFC_IND_2024.csv    ← novo
├── {TICKER}_DFP_DVA_CON_2024.csv    ← novo (se disponível)
├── {TICKER}_DFP_DVA_IND_2024.csv    ← novo (se disponível)
├── {TICKER}_DFP_DMPL_CON_2024.csv   ← novo (se disponível)
├── {TICKER}_DFP_DMPL_IND_2024.csv   ← novo (se disponível)
├── {TICKER}_DFP_BPA_CON_2024.csv    ← existente → verificar/materializar
├── {TICKER}_DFP_BPP_CON_2024.csv    ← existente → verificar/materializar
└── ... (~88 tickers × 12 tipos × 2 períodos = até ~2.100 arquivos)

docs/
└── M017_S02.5_DATASET_AUDIT.md      ← relatório final

src/ingestion/
└── cvm_dataset_sync.py              ← script reutilizável para futuros downloads CVM
                                        (parâmetros: tickers=None→todos, tipos, anos)
```

### Critérios de Aceite (S02.5-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | Auditoria cloud-only concluída: lista de arquivos placeholder identificada | seção "Cloud-Only" no relatório |
| AC-02 | DRE_CON e DFC_CON presentes localmente para ≥ 15 dos 17 tickers NEEDS_FINANCIALS Track B | `os.path.getsize() > 0` para cada arquivo |
| AC-03 | Cada arquivo baixado abre sem erro e tem ≥ 1 linha de dados (head 5 linhas) | verificação de integridade no script |
| AC-04 | BPA_CON e BPP_CON materializados localmente (não cloud-only) para ≥ 15 tickers NEEDS_FINANCIALS | mesma verificação |
| AC-05 | `cvm_dataset_sync.py` criado com função `sync_ticker_dataset(tickers=None, tipos, anos)` — `tickers=None` = todos os mapeados | arquivo presente |
| AC-06 | Inventário gerado para **todos** os tickers com CNPJ mapeado (não apenas os 18) | contagem no relatório |
| AC-07 | Relatório `docs/M017_S02.5_DATASET_AUDIT.md` criado com tabela: ticker × tipo × local/cloud/ausente/baixado | arquivo presente |
| AC-08 | Subseção específica dos 18 NEEDS_FINANCIALS com status detalhado presente no relatório | seção "18 NEEDS_FINANCIALS" no relatório |
| AC-09 | Recomendação objetiva para S03 documentada (quais tickers têm dataset completo) | seção "Recomendação S03" no relatório |
| AC-10 | 0 CSVs lidos inteiros no contexto — apenas `pd.read_csv(..., nrows=5)` para verificação | code review |
| AC-11 | Credenciais ou tokens não usados — CVM endpoint é público | sem `.env` necessário |
| AC-12 | AUAU3 (CNPJ nulo) e PETZ3 (LEGACY) documentados como excluídos do download | seção "Exclusões" no relatório |

### Relatório obrigatório — `M017_S02.5_DATASET_AUDIT.md`

Estrutura do relatório:

```markdown
# M017-S02.5 — CVM Dataset Audit Report

## 1. Resumo Executivo
- N tickers cobertos (universo mapeado com CNPJ)
- N arquivos encontrados (locais)
- N arquivos cloud-only (OneDrive placeholders)
- N arquivos baixados da CVM
- N arquivos ainda ausentes após S02.5

## 2. Inventário Completo por Ticker (universo amplo)
| Ticker | CNPJ | Setor | BPA_CON | BPP_CON | DRE_CON | DFC_CON | DVA_CON | DMPL_CON | Status Geral |

## 3. Subseção — 18 NEEDS_FINANCIALS (validação prioritária M017)
| Ticker | BPA_CON | BPP_CON | DRE_CON | DFC_CON | DVA_CON | DMPL_CON | Pronto p/ S03 |
(foco nos tipos críticos que desbloqueiam os modelos M016)

## 4. Arquivos Cloud-Only
Lista de caminhos que eram placeholders + ação tomada

## 5. Arquivos Baixados
Lista de arquivos novos + URL fonte + tamanho

## 6. Arquivos Ainda Ausentes
Lista com justificativa (ex: ticker não aparece nos CSVs CVM — empresa nova ou sem obrigação)

## 7. Exclusões
- AUAU3: CNPJ nulo em cvm_codes.yaml — não baixar
- PETZ3: LEGACY_TICKER permanente — não baixar (evitar poluição de dataset)

## 8. Recomendação para S03
- Tickers com dataset completo (todos os tipos críticos): lista
- Tickers com dataset parcial (apenas DRE ou apenas DFC): lista + impacto
- Tickers bloqueados (nenhum arquivo): lista
- Prioridade de execução S03: 18 NEEDS_FINANCIALS primeiro, demais em batch
```

### Riscos S02.5

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| ZIPs CVM indisponíveis ou URL alterada | Baixa | Alto | Verificar URL antes de assumir estrutura; fallback para download manual com instrução ao usuário |
| Ticker não encontrado nos CSVs CVM (empresa nova, pequena ou sem obrigação CVM) | Média | Baixo | Documentar como ausente no relatório; não bloquear S02.5 |
| Arquivos OneDrive cloud-only não materializáveis sem login OneDrive | Média | Alto | Baixar da CVM diretamente (não depender do OneDrive) — preferência explícita |
| CSVs CVM anuais muito grandes para filtrar em memória (~88 tickers) | Média | Médio | Usar `chunksize` no pandas para filtrar por CD_CVM sem carregar inteiro |
| CNPJ de um ticker não mapeado no sistema | Baixa | Baixo | `cvm_codes.yaml` cobre ~88 tickers; AUAU3 (null) e PETZ3 (legacy) excluídos explicitamente |
| Tempo de download elevado para universo amplo (~88 tickers × 12 tipos) | Média | Baixo | Execução em batches; paralelismo opcional; script é reutilizável — rodar fora de horário se necessário |

---

## S03 — Metric Extraction Engine

### Objetivo
Implementar `src/parsers/cvm_extractor.py` — extrator que lê os CSVs CVM (Track B)
e os xlsx do pipeline (Track A) e produz os 9 campos financeiros normalizados para cada ticker.

**Escopo de parsing:** o dataset amplo construído em S02.5 (todos os tickers mapeados).
**Prioridade de validação:** primeiros testes e smoke tests nos 18 tickers NEEDS_FINANCIALS —
que desbloqueiam os modelos M016. Restante do universo é executado em batch subsequente.

### Escopo
- **Criar:** `src/parsers/cvm_extractor.py` — motor de extração Track B (CVM CSV), opera sobre dataset amplo
- **Criar:** `src/parsers/excel_extractor.py` — extrator Track A (xlsx pipeline) para 9 tickers NEEDS_FINANCIALS
- **Reutilizar/adaptar:** `dfp_parser.py` conforme decisão de S02
- **Implementar:** lógica hierárquica de conta CVM (tentativa primária → fallback → missing)
- **Garantir:** cada valor extraído tem `source_file` + linha de origem rastreável
- **Estratégia de teste:** validar extração 1 ticker (EGIE3) → batch 18 NEEDS_FINANCIALS → batch universo amplo

### Lógica de extração por campo

```python
# Pseudocódigo — hierarquia de busca por conta
def extract_ebitda(dre_df, dfc_df):
    # 1a tentativa: linha EBITDA direta (algumas empresas reportam)
    ebitda = find_account(dre_df, patterns=["EBITDA", "Lajida"])
    if ebitda is not None:
        return ebitda, "DRE_DIRECT"
    
    # 2a tentativa: EBIT + D&A
    ebit = find_account(dre_df, patterns=["Resultado antes do resultado financeiro", "EBIT", "Lajir"])
    da = find_account(dre_df, patterns=["Depreciação", "Amortização", "D&A"])
    if ebit is not None and da is not None:
        return ebit + abs(da), "DRE_EBIT_PLUS_DA"
    
    # 3a tentativa: DFC método indireto (ajustes de D&A explícitos)
    ebit_dfc = find_account(dfc_df, patterns=["Resultado líquido do período"])
    da_dfc = find_account(dfc_df, patterns=["Depreciação e amortização"])
    if ebit_dfc is not None and da_dfc is not None:
        return ebit_dfc + abs(da_dfc), "DFC_INDIRECT"
    
    return None, "MISSING"
```

### Critérios de Aceite (S03-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `cvm_extractor.extract(ticker)` retorna dict com 9 campos + `source_file` por campo | teste unitário |
| AC-02 | Campos ausentes retornam `None` (nunca imputado, nunca estimado) | assert `None` não é `0` |
| AC-03 | `excel_extractor.extract(ticker)` retorna dict equivalente para Track A | teste unitário |
| AC-04 | Quando Track A e Track B disponíveis, Track B é autoritário | teste de precedência |
| AC-05 | `source_file` e linha de origem populados para cada campo não-None | campo `extraction_notes` |
| AC-06 | Extração funcional para ≥ 15 dos 17 tickers Track B | smoke test batch |
| AC-07 | VAMO3 retorna todos os campos como `None` com `source_track=MANUAL_REVIEW` | assert |
| AC-08 | 0 mocks; 0 valores imputados | code review |
| AC-09 | `input_hash` calculado como hash de (ticker + reference_date + source_file) | verificar campo |

### Riscos S03

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| EBITDA não encontrado em ≥ 3 tickers (conta com nome atípico) | Alta | Médio | Hierarquia de fallback documentada em S02; expandir patterns em S03 |
| `shares_outstanding` ausente em todos os CSVs CVM | Alta | Alto | Fallback para `cotahist_daily` × número de ações (market_cap / price); documentar como `source_track=B3_MARKET_DATA`; confidence penalizada nos modelos |
| DFP anual vs ITR trimestral: EBITDA anualizado erroneamente | Média | Alto | Usar sempre DFP anual como primário; ITR como suplemento para data mais recente |
| free_cash_flow negativo em MGLU3/PCAR3 (distressed) | Alta | Baixo | Correto — extrair o valor real; modelo já tem flag `DISTRESSED` para EBITDA/FCF negativo |

---

## S04 — Populate Financial Inputs

### Objetivo
Executar os extratores do S03 contra todos os tickers elegíveis e popular
`valuation_financial_inputs` no banco. Gate de inserção: somente quando
`input_hash` não existe na tabela (evita re-inserção).

### Escopo
- **Executar:** `cvm_extractor.extract(ticker)` para 17 tickers Track B
- **Executar:** `excel_extractor.extract(ticker)` para 9 tickers Track A (suplementar)
- **Inserir:** via `financial_inputs_store.upsert_inputs()` (criado em S01)
- **Produzir:** relatório de cobertura pós-inserção por ticker e campo

### Lógica de inserção

```
Para cada ticker em NEEDS_FINANCIALS (exceto VAMO3):
  1. Extrair via Track B (CVM CSV) → resultado_b
  2. Se Track A disponível: extrair via Track A (xlsx) → resultado_a
  3. Merged = resultado_b  # Track B é autoritário
  4. Para campos None em resultado_b E não-None em resultado_a:
       Merged[campo] = resultado_a[campo]  # Track A preenche gaps
       Merged["source_track"][campo] = "EXCEL_PIPELINE_SUPPLEMENTAL"
  5. upsert_inputs(ticker, Merged)  # INSERT OR REPLACE se input_hash mudou
  6. Log: campos populados, campos None, source_track por campo
```

### Critérios de Aceite (S04-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `valuation_financial_inputs` populada para ≥ 15 tickers | `SELECT COUNT(DISTINCT ticker)` |
| AC-02 | VAMO3 não inserido (MANUAL_REVIEW — sem fonte) | `SELECT * WHERE ticker='VAMO3'` → 0 rows |
| AC-03 | Tickers PRESERVE_EXISTING não inseridos (fora de escopo M017) | `SELECT * WHERE ticker IN ('BBAS3', ...)` → 0 rows |
| AC-04 | PETZ3 não inserido | `SELECT * WHERE ticker='PETZ3'` → 0 rows |
| AC-05 | `input_hash` populado em todas as linhas | `SELECT * WHERE input_hash IS NULL` → 0 rows |
| AC-06 | Constraint UNIQUE não violada (re-run idempotente) | executar inserção 2× sem erro |
| AC-07 | Banco não corrompido | `PRAGMA integrity_check` |
| AC-08 | Relatório `docs/M017_S04_POPULATION_REPORT.md` gerado com cobertura por ticker/campo | arquivo criado |
| AC-09 | 0 fair_values calculados | nenhuma escrita em `asset_intelligence_snapshots` |

### Riscos S04

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| Inserção parcial por erro de parsing em 1 ticker contamina lote | Média | Médio | Transação por ticker — erro em KLBN11 não afeta HYPE3 |
| `reference_date` inconsistente entre DFP e ITR do mesmo ticker | Média | Médio | Usar a data mais recente disponível; documentar em `extraction_notes` |
| Campos críticos None em > 5 tickers após inserção | Média | Alto | Logar como `PARTIAL_INPUTS`; modelos já bloqueiam quando input ausente |
| VAMO3 inadvertidamente inserido com valores zerados | Baixa | Alto | Assert explícito antes de upsert: se `source_track=MANUAL_REVIEW` → skip |

---

## S05 — Model Re-run Readiness

### Objetivo
Verificar que os modelos de valuation (M016) lêem corretamente `valuation_financial_inputs`
e que cada ticker com dados populados seria processado sem erros. **Não calcula fair_value.**
Entrega: relatório de prontidão por ticker — quais estão prontos para calcular em M018.

### Escopo
- **Adaptar:** funções `diagnose_*_tickers()` para ler `valuation_financial_inputs`
  (atualmente bloqueiam com `NEEDS_FINANCIALS` pois a tabela não existe)
- **Executar:** diagnose batch dry-run para todos os 18 tickers com `write=False`
- **Produzir:** relatório `docs/M017_S05_READINESS_REPORT.md` com status por ticker:
  `READY_TO_CALCULATE` | `PARTIAL_INPUTS` | `NEEDS_FINANCIALS` | `MANUAL_REVIEW`
- **Confirmar:** 9 fair values PRESERVE_EXISTING não alterados
- **Confirmar:** 514 testes M016 ainda passando

### O que NÃO faz
- Não calcula fair_value
- Não escreve em `asset_intelligence_snapshots`
- Não altera modelos de valuation

### Status de prontidão (definições)

| Status | Critério | Próximo passo |
|--------|----------|---------------|
| `READY_TO_CALCULATE` | Todos os campos críticos presentes (ebitda, fcf ou net_debt + shares) | M018: executar modelo |
| `PARTIAL_INPUTS` | ≥ 1 campo crítico presente; ≥ 1 ausente | M018: investigar campo ausente |
| `NEEDS_FINANCIALS` | 0 campos críticos presentes na tabela | Fonte alternativa ou skip |
| `MANUAL_REVIEW` | Sem fonte disponível (VAMO3) | Investigação manual |

### Critérios de Aceite (S05-AC)

| # | Critério | Verificação |
|---|----------|-------------|
| AC-01 | `diagnose_*_tickers()` lê `valuation_financial_inputs` sem erro | execução batch sem exception |
| AC-02 | ≥ 12 tickers com status `READY_TO_CALCULATE` ou `PARTIAL_INPUTS` | relatório S05 |
| AC-03 | VAMO3 = `MANUAL_REVIEW` | assert no relatório |
| AC-04 | 9 fair values PRESERVE_EXISTING inalterados | diagnose bank + commodity + industry |
| AC-05 | PETZ3 permanece `LEGACY_TICKER` | assert |
| AC-06 | VALE3/AUAU3/NTCO3 permanecem fora do scope | assert |
| AC-07 | 514/514 testes M016 passando | `pytest tests/` |
| AC-08 | `write=False` em todos os dry-runs | code review |
| AC-09 | Relatório `docs/M017_S05_READINESS_REPORT.md` criado | arquivo presente |

### Riscos S05

| Risco | Probabilidade | Impacto | Mitigação |
|-------|:-------------:|:-------:|-----------|
| `diagnose_*_tickers()` tem path hardcoded que ignora `valuation_financial_inputs` | Alta | Alto | Refatorar em S05 como parte do escopo; não é alteração de modelo de cálculo |
| Testes M016 quebram por mudança no schema do DB | Baixa | Médio | Rodar testes antes e depois de cada migration |
| < 10 tickers chegam em `READY_TO_CALCULATE` — extração insuficiente | Média | Médio | Documentar gap; M018 resolve — M017 não é bloqueado por threshold de prontidão |

---

## SXX — CVM Ingestion VALE3 / NTCO3 / AUAU3

### Objetivo
Ingestão de RI docs CVM para os 3 tickers bloqueados. **Paralelo a S01–S05 — não bloqueia.**
Herdado de M016-SXX (não executado).

### Restrições
- VALE3: priority=high; `type=mining` → canonical=COMMODITY; já tem modelo pronto
- NTCO3: `type` a confirmar; modelo industry disponível
- AUAU3: successor de PETZ3; empresa nova; prazo CVM correndo
- **Nenhum dos três entra em M017 sem ri_docs_count > 0 confirmado**

### Critérios de Aceite (SXX-AC)

| # | Critério |
|---|----------|
| AC-01 | VALE3: `ri_docs_count > 0` após SXX |
| AC-02 | NTCO3: `ri_docs_count > 0` após SXX |
| AC-03 | VALE3 automaticamente elegível para M018 após SXX + M017 |
| AC-04 | AUAU3: ingestão só se docs CVM disponíveis; não forçar |
| AC-05 | PETZ3 **não recebe docs** — LEGACY_TICKER permanente |

---

## Regras Imutáveis (Invariantes M017)

```
RULE-01  Não calcular fair_value em M017 — apenas popular valuation_financial_inputs
RULE-02  Não sobrescrever fair values existentes (BBAS3/ITUB4/PETR4/WEGE3 etc.)
RULE-03  Não alterar modelos de valuation (bank_model, commodity_model, etc.)
RULE-04  Não inventar EBITDA, FCF, net_debt ou shares — dado ausente = None, não estimativa
RULE-05  PETZ3 permanece LEGACY_TICKER para sempre
RULE-06  VALE3/AUAU3/NTCO3 só entram em M017 após SXX confirmar ri_docs_count > 0
RULE-07  VAMO3 permanece NEEDS_FINANCIALS — sem fonte disponível, não criar mock
RULE-08  Track B (CVM CSV) é autoritário; Track A (Excel) apenas suplementa campos ausentes
RULE-09  Cada valor inserido em valuation_financial_inputs tem source_file rastreável
RULE-10  input_hash obrigatório em toda linha de valuation_financial_inputs
RULE-11  Não alterar opções/OOS/paper/scheduler
RULE-12  S01 (schema) deve ser concluída e testada ANTES de S02/S03/S04
RULE-13  write=False em todos os dry-runs de S05
RULE-14  514 testes M016 devem continuar passando ao final de M017
RULE-15  S02.5 baixa para todos os tickers com CNPJ mapeado em cvm_codes.yaml; 18 NEEDS_FINANCIALS são a prioridade de validação, não o limite do dataset
RULE-16  S02.5 não lê CSV inteiro no contexto — pd.read_csv(..., nrows=5) apenas para verificação
RULE-17  S02.5 prefere download direto da CVM a depender de sync OneDrive em tempo de execução
RULE-18  S02.5 exclui AUAU3 (CNPJ nulo) e PETZ3 (LEGACY_TICKER) do download — documentar como exclusões explícitas no relatório
RULE-19  S03 parseia o dataset amplo (universo completo); primeiros testes e smoke tests são nos 18 NEEDS_FINANCIALS
```

---

## Ordem de Execução

```
╔══════════════════════════════════════════════════════════╗
║  FASE 1 — BLOQUEADORA (executar antes de tudo)          ║
╠══════════════════════════════════════════════════════════╣
║  M017-S01: Schema Design                        ✅ DONE ║
║  → CREATE TABLE valuation_financial_inputs              ║
║  → financial_inputs_store.py com upsert/get/list        ║
║  → PRAGMA integrity_check após migration                ║
╚══════════════════════════════════════════════════════════╝
              ↓ S01 PASSED ✅
╔══════════════════════════════════════════════════════════╗
║  FASE 2 — AUDITORIA (executar após S01)         ✅ DONE ║
╠══════════════════════════════════════════════════════════╣
║  M017-S02: DFP/ITR Parser Audit                         ║
║  → Auditar dfp_parser.py existente                      ║
║  → Mapear cobertura 17 tickers × 9 campos               ║
║  → Decisão: reutilizar vs reescrever parser             ║
║                                                          ║
║  M017-SXX: CVM Ingestion (paralelo, independente)       ║
╚══════════════════════════════════════════════════════════╝
              ↓ S02 PASSED ✅
╔══════════════════════════════════════════════════════════╗
║  FASE 2.5 — DATASET (desbloqueador para S03)   ⬜ NEXT  ║
╠══════════════════════════════════════════════════════════╣
║  M017-S02.5: CVM Full Dataset Localizer/Downloader      ║
║  → Auditar cloud-only vs local (OneDrive placeholders)  ║
║  → Baixar DRE_CON/IND, DFC_CON/IND, DVA, DMPL da CVM  ║
║  → Materializar BPA/BPP cloud-only                     ║
║  → Relatório: encontrado/cloud-only/baixado/ausente     ║
║  → Recomendação objetiva para S03                       ║
╚══════════════════════════════════════════════════════════╝
              ↓ S02.5 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 3 — EXTRAÇÃO (executar após S02.5)                ║
╠══════════════════════════════════════════════════════════╣
║  M017-S03: Metric Extraction Engine                     ║
║  → cvm_extractor.py (Track B — 17 tickers)              ║
║  → excel_extractor.py (Track A — 9 tickers)             ║
║  → Testes unitários por extrator                        ║
╚══════════════════════════════════════════════════════════╝
              ↓ S03 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 4 — INSERÇÃO (executar após S03)                  ║
╠══════════════════════════════════════════════════════════╣
║  M017-S04: Populate Financial Inputs                    ║
║  → Batch extração + upsert para ≥ 15 tickers            ║
║  → Relatório de cobertura por campo                     ║
╚══════════════════════════════════════════════════════════╝
              ↓ S04 PASSED
╔══════════════════════════════════════════════════════════╗
║  FASE 5 — VALIDAÇÃO (executar após S04)                 ║
╠══════════════════════════════════════════════════════════╣
║  M017-S05: Model Re-run Readiness                       ║
║  → diagnose batch dry-run com write=False               ║
║  → Relatório READY_TO_CALCULATE por ticker              ║
║  → 514/514 testes M016 passando                         ║
╚══════════════════════════════════════════════════════════╝
```

---

## Success Criteria — M017

| Critério | Target |
|----------|--------|
| `valuation_financial_inputs` criada e populada | ≥ 15 tickers |
| Campos críticos presentes (ebitda OU fcf) por ticker | ≥ 12 tickers |
| Tickers `READY_TO_CALCULATE` para M018 | ≥ 10 |
| 9 fair values PRESERVE_EXISTING inalterados | 100% — 0 sobrescrições |
| PETZ3 permanece LEGACY_TICKER | 100% |
| 514 testes M016 continuam passando | 514/514 |
| 0 valores inventados / imputados | 0 |
| 0 fair_values calculados em M017 | 0 |
| VAMO3 documentado como MANUAL_REVIEW | 100% |

---

## Riscos Arquiteturais Transversais

| ID | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|:-------------:|:-------:|-----------|
| R01 | CSVs CVM com estrutura hierárquica multi-nível (conta pai/filho) dificulta lookup por nome | **Alta** | **Alto** | Usar código de conta CVM (ex: "3.01.01") como identificador primário, não nome literal |
| R02 | `shares_outstanding` não disponível em nenhuma demonstração CVM estruturada | **Alta** | **Alto** | Fallback calculado: `market_cap / price` via `cotahist_daily`; documentar penalidade de confidence |
| R03 | EBITDA negativo em MGLU3/PCAR3 → extrator retorna valor real negativo que confunde modelos | Alta | Médio | Extrair e inserir valor real negativo; modelos já têm flag DISTRESSED — comportamento correto |
| R04 | DFP de múltiplos anos disponíveis — extrator usa ano errado | Média | Alto | Priorizar DFP mais recente (2024 ou 2025); documentar `fiscal_year` por linha |
| R05 | `dfp_parser.py` existente incompatível com scanner_quant — reescrita necessária | Média | Alto | S02 audita antes; se reescrita, escopo de S03 aumenta — ajustar estimate |
| R06 | VAMO3 com dados disponíveis em fonte não catalogada (RI manual, B3 API) | Baixa | Baixo | Documentar como MANUAL_REVIEW; investigação é escopo M018+ |

---

## Dependências Técnicas

### Arquivos existentes relevantes

```
data/database/scanner_quant.db                     ← banco canônico (recebe migration S01)
12_PYTHON/src/parsers/dfp_parser.py                ← parser existente — auditar em S02
12_PYTHON/data/raw/cvm/2025/                       ← CSVs CVM 17 tickers (Track B)
12_PYTHON/pipeline banco completo/outputs/         ← xlsx 9 tickers (Track A)
12_PYTHON/data/processed/*/dfp_{year}.json         ← JSONs pré-processados (parcial)
src/valuation/models/bank_model.py                 ← _extract_fair_value_from_excel() — adaptar
src/valuation/models/commodity_model.py            ← diagnose_commodity_tickers() — adaptar S05
src/valuation/models/utility_model.py              ← diagnose_utility_tickers() — adaptar S05
src/valuation/models/retail_model.py               ← diagnose_retail_tickers() — adaptar S05
src/valuation/models/industry_model.py             ← diagnose_industry_tickers() — adaptar S05
```

### Novos arquivos a criar em M017

```
src/parsers/financial_inputs_store.py        ← S01 ✅ (CRUD para valuation_financial_inputs)
src/ingestion/cvm_dataset_sync.py            ← S02.5 (download CVM filtrado por ticker)
src/parsers/cvm_extractor.py                 ← S03 (Track B — CVM CSV)
src/parsers/excel_extractor.py               ← S03 (Track A — xlsx pipeline)
migrations/001_valuation_financial_inputs.sql ← S01 ✅ (migration DDL)
tests/test_financial_inputs_store.py          ← S01 ✅
tests/test_cvm_extractor.py                  ← S03
tests/test_excel_extractor.py                ← S03
docs/M017_CVM_FIELD_MAPPING.md               ← S01 ✅ (conta CVM → campo normalizado)
docs/M017_S02_PARSER_AUDIT.md               ← S02 ✅ (auditoria do dfp_parser)
docs/M017_S02.5_DATASET_AUDIT.md            ← S02.5 (cloud-only + downloaded + absent + recomendação)
docs/M017_S04_POPULATION_REPORT.md          ← S04 (cobertura pós-inserção)
docs/M017_S05_READINESS_REPORT.md           ← S05 (prontidão para M018)
```

---

## Decisões Registradas M017

| ID | Decisão |
|----|---------|
| D111 | Two-track approach: Track A (Excel pipeline, 9 tickers) + Track B (CVM CSV, 17 tickers) — Track B é autoritário |
| D112 | `valuation_financial_inputs` = tabela canônica para inputs financeiros estruturados |
| D113 | VAMO3 = MANUAL_REVIEW — sem fonte disponível; não criar mock; não bloquear M017 |
| D114 | `dfp_parser.py` de 12_PYTHON a ser auditado em S02 antes de qualquer adaptação |
| D115 | `shares_outstanding` sem fonte CVM CSV → fallback `market_cap/price` via `cotahist_daily` |
| D116 | `ri_documents.extracted_text` = empty (0/3.251) — não é fonte viável para M017 |
| D117 | M017 não calcula fair_value — apenas popula `valuation_financial_inputs`; modelos M016 calculam em M018 |
| D118 | `input_hash` obrigatório em `valuation_financial_inputs` como gate de re-extração |
| D119 | Código de conta CVM (numérico) é identificador primário; nome literal é fallback secundário |
| D120 | Track A preenche apenas campos None do Track B — não sobrepõe valores já extraídos via CVM |
| D121 | S02.5 inserida antes de S03: S02 revelou arquivos cloud-only + DRE/DFC ausentes; S03 não pode parsear o que não existe localmente — resolver dataset antes de implementar extrator |
| D122 | S02.5 cobre universo amplo (todos os tickers com CNPJ mapeado, ~88); 18 NEEDS_FINANCIALS são prioridade de validação M017, não limite estrutural do dataset — dataset deve ser reutilizável para valuation, radar, coverage e expansões futuras |
| D123 | AUAU3 (CNPJ nulo) e PETZ3 (LEGACY_TICKER) excluídos do download S02.5 — exclusões documentadas explicitamente no relatório, não ignoradas silenciosamente |

---

## Notas de Execução

1. **S01 e S02 concluídas** — schema criado, parser auditado, cobertura mapeada.
2. **S02.5 é o próximo passo** — dataset cloud-only e DRE/DFC ausentes bloqueiam S03; resolver primeiro. **Dataset alvo: universo amplo (~88 tickers com CNPJ mapeado), não apenas os 18.**
3. **S02.5 usa endpoint CVM público** — `dados.cvm.gov.br` não requer autenticação; baixar ZIP anual e filtrar por ticker/CD_CVM.
4. **Verificar `cvm_codes.yaml`** — contém CNPJ + CD_CVM por ticker; usar para filtrar os ZIPs CVM sem abrir CSV inteiro. AUAU3 (null) e PETZ3 (LEGACY) excluídos do download.
5. **S02.5 usa chunksize obrigatório** — ZIPs CVM têm todas as empresas abertas do Brasil; filtrar em chunks por CD_CVM, nunca carregar inteiro.
6. **S03 só inicia após S02.5 PASSED** — não tentar extração antes de confirmar todos os arquivos DRE/DFC locais.
7. **S03 parseia dataset amplo, testa nos 18 primeiro** — EGIE3 como canário (Track A + B), depois batch 18 NEEDS_FINANCIALS, depois universo completo.
8. **MGLU3/PCAR3** — esperar FCF negativo; é dado real, não erro de extração.
9. **SXX é independente** — pode ser executado em paralelo por processo separado sem interferência.
10. **M017 termina com `write=False`** — fair values calculados são escopo de M018.

---

*Roadmap M017 criado em 2026-05-25.*  
*Atualizado em 2026-05-25 — inserida S02.5 (CVM Full Dataset Localizer/Downloader) após confirmação de arquivos cloud-only e DRE/DFC ausentes em S02.*  
*Atualizado em 2026-05-25 — S02.5 expandida para universo amplo (~88 tickers com CNPJ mapeado); 18 NEEDS_FINANCIALS = prioridade de validação, não limite do dataset; S03 = parser dataset amplo com primeiros testes nos 18. Decisões D122 e D123 registradas. RULE-15 e RULE-19 atualizadas.*  
*Baseado em: M016-CLOSED.md · M016-VALIDATION.md · auditoria de fontes (scanner_quant.db + CVM CSVs + xlsx pipeline)*  
*Próxima etapa: `/gsd-execute-phase M017-S02.5` — aguardando autorização.*
