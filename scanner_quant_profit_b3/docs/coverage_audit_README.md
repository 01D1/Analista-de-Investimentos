# Cobertura de Valuation — Auditoria por Ticker

**Data de execução:** 2026-05-23  
**Escopo:** Watchlist de 9 tickers da `config.yaml`  
**Objetivo:** Levantar o estado atual de cobertura de dados fundamentalistas e valuation, sem alterar dados, sem criar mocks, sem calcular valuation.

---

## Arquivos Gerados

| Arquivo | Conteúdo |
|---|---|
| `coverage_audit_YYYYMMDD.csv` | Dados estruturados por ticker — uma linha por ativo |
| `S01-SUMMARY.md` | Este relatório narrativo |

---

## Descrição das Colunas do CSV

### Identificação

| Coluna | Descrição | Valores válidos |
|---|---|---|
| `ticker` | Código do ativo na B3 (.SA omitido) | texto (ex: PETR4) |
| `ticker_type` | Classificação setorial preliminar do ativo | BANK, COMMODITY, ENERGY, INDUSTRIAL |
| `ai_present` | Se existe entrada em `asset_intelligence_snapshots` | TRUE / FALSE |

### Dados Cadastrais

| Coluna | Descrição | NULL significa |
|---|---|---|
| `company_name` | Nome social da empresa | Não foi populado via pipeline — a tabela `asset_intelligence_snapshots` tem o campo vazio para todos os tickers da watchlist |
| `sector` | Setor econômico principal | Não foi populado via pipeline — NULL para todos |
| `subsector` | Subsetor (BNDES/BMF, Energia, etc.) | Não foi populado via pipeline — NULL para todos |

### Preço Histórico

| Coluna | Descrição | NULL significa |
|---|---|---|
| `price_history_first` | Primeira data com registro em `cotahist_daily` | Nunca coletado para este ticker |
| `price_history_last` | Última data com registro em `cotahist_daily` | Nunca coletado para este ticker |
| `price_history_rows` | Total de linhas de preço para o ticker | 0 = nunca coletado |

### Dados CVM / Regulatórios

| Coluna | Descrição | NULL significa |
|---|---|---|
| `cvm_docs_count` | Número de documentos em `ri_documents` (CVM IPE/DFP/ITR) | 0 = nenhum documento coletado |
| `cvm_latest_doc` | Data de publicação do documento mais recente | NULL = nenhum documento |

### Eventos de Mercado

| Coluna | Descrição | NULL significa |
|---|---|---|
| `events_count` | Total de eventos em `market_events` | 0 = nenhum evento |
| `events_last` | Data do último evento | NULL = nenhum evento |
| `sector_from_events` | Setor inferido da tabela `market_events` | NULL = setor não foi populado nos registros deste ticker |

### Metodologia de Valuation

| Coluna | Descrição | NULL significa |
|---|---|---|
| `methodology` | Metodologia setorial aplicável ao ticker | **Nunca NULL neste audit** — inferida da classificação da watchlist conforme regras de negócio do projeto |

**Nota sobre `methodology`:** O campo `valuation_method` em `asset_intelligence_snapshots` é NULL para todos os tickers. O audit atribui a metodologia aplicável com base na classificação known:

- **BANK** → `COSIF_BANK` — usa COSIF (não IFRS); métricas NIM/ROE/DDM em vez de EBITDA/DCF
- **COMMODITY** → `COMMODITY_DCF` — mineração/celulose; DCF com fluxo de caixa livre
- **ENERGY** → `ENERGY_DCF` — petróleo; DCF com cenários de produção
- **INDUSTRIAL** → `INDUSTRIAL_DCF` — industriais diversificados; DCF padrão

### Valuation e Preço de Mercado

| Coluna | Descrição | NULL significa |
|---|---|---|
| `valuation_available` | Flag `valuation_available` em `asset_intelligence_snapshots` | NULL = ticker sem entrada em AI; 0 = flag indica que não há valuation; 1 = flag indica que há valuation |
| `fair_value` | Preço-alvo sintetizado pelo modelo | Não foi calculado/injetado — não confundir com dado inventado |
| `market_price` | Preço de mercado atual no snapshot | Não foi populado via pipeline — NULL para todos |
| `upside_pct` | (fair_value / market_price) - 1, em % | NULL = fair_value ou market_price ausentes |
| `valuation_method` | Método de valuation reportado pelo pipeline | NULL = pipeline nunca populou este campo |
| `fundamental_quality_score` | Score de qualidade fundamentalista (0–1) | NULL = nunca calculado/populado |

### Volatilidade e Risco

| Coluna | Descrição | NULL significa |
|---|---|---|
| `ensemble_vol` | Volatilidade implícita组合 do ticker | Nunca calculado para este ticker |
| `volatility_regime` | Regime de volatilidade (VOL_NORMAL, VOL_ELEVADA, etc.) | Nunca calculado |
| `technical_score` | Score técnico final | Não disponível |
| `technical_status` | Status do setup técnico | NULL = não calculado |
| `risk_status` | Status de risco do ativo | NULL = não calculado |

### Governança Integrada

| Coluna | Descrição | NULL significa |
|---|---|---|
| `integrated_status` | Status integrado do ativo (ALTA_CONVERGENCIA, APENAS_MONITORAR_SOFT_COVERAGE, etc.) | Ticker sem entrada em AI |

### Classificação de Gaps

| Coluna | Descrição |
|---|---|
| `gaps` | Lista de lacunas pipe-separated (`\|`) |
| `gap_count` | Número total de gaps identificados |

### Significado de NULL/missing por cenário

| Cenário | Significado real |
|---|---|
| `fair_value = NULL` em ticker com `valuation_available=1` | O pipeline populou a flag mas nunca calculou/injetou o valor real |
| `valuation_available = NULL` | Ticker não tem entrada em `asset_intelligence_snapshots` (BPAC11, SANB11) |
| `valuation_method = NULL` em todos | O pipeline nunca populou este campo em nenhum ticker |
| `fundamental_quality_score = NULL` em todos | Score nunca calculado/populado pelo pipeline |
| `company_name = NULL` em todos | O pipeline populou `company_name` em nenhum ticker |
| `sector = NULL` em todos | O pipeline populou `sector` em nenhum ticker |
| `market_price = NULL` em todos | O pipeline populou `market_price` em nenhum ticker |
| `cvm_docs_count = 0` | Nenhum documento CVM coletado (BPAC11, SANB11, SUZB3, VALE3) |

---

## Regras de Não-InVASÃo

Este audit **NÃO** executa:

1. Inserção ou alteração no banco de dados
2. Criação de dados mockados/fictícios
3. Cálculo de valuation pesado (DCF, Gordon, múltiplos)
4. Modificação no frontend (`pages/`)
5. Alteração em opções, OOS, paper trading, scheduler
5. Invenção de `fair_value` — valores existentes no banco foram preservados como-leitos
6. Preenchimento de campos NULL

---

## Descobertas Adicionais — Discrepância CVM

| Ticker | `data_source_traceability` (REGULATORY) | `ri_documents` real | Status |
|---|---|---|---|
| BBAS3 | 6.100 | 121 | OK |
| BBDC4 | 6.100 | 125 | OK |
| ITUB4 | 6.100 | 125 | OK |
| PETR4 | 6.100 | 131 | OK |
| WEGE3 | 6.100 | 124 | OK |
| **BPAC11** | 6.100 | **0** | ⚠️ **DISCREPÂNCIA** — coleta registrada mas documentos não inseridos |
| **SANB11** | 6.100 | **0** | ⚠️ **DISCREPÂNCIA** — coleta registrada mas documentos não inseridos |
| **SUZB3** | 6.100 | **0** | ⚠️ **DISCREPÂNCIA** — coleta registrada mas documentos não inseridos |
| **VALE3** | **0** | **0** | ⚠️ **SEM TRACE NEM DADOS** — pipeline nunca executado para este ticker |

Para BPAC11, SANB11 e SUZB3, o pipeline registrou 6.100 registros em `data_source_traceability`, mas `ri_documents` está vazia — falha entre coleta e inserção. VALE3 nem tem entrada em traceability.

---

## Classificação de Gaps

### Tipo 1 — Dados Ausentes (bloqueadores críticos)
| Gap | Ticker's | Impacto |
|---|---|---|
| `CVM_DOCS_MISSING` | BPAC11, SANB11, SUZB3, VALE3 | Sem demonstrações financeiras → impossível calcular valuation fundamentalista |
| `PRICE_HISTORY_MISSING` | Nenhum | Cotahist completo para todos os 9 tickers |

### Tipo 2 — Setor Ausente (impossibilita roteamento)
| Gap | Ticker's | Impacto |
|---|---|---|
| `SECTOR_MISSING` | 7 tickers com AI entry | Pipeline não popula `sector` em AI → impossibilita roteamento automático |

### Tipo 3 — Metodologia Ausente (bloqueador de valuation)
| Gap | Ticker's | Impacto |
|---|---|---|
| `VALUATION_METHOD_MISSING` | 7 tickers com AI entry | Pipeline não popula `valuation_method` → nenhum ticker reporta o modelo |

### Tipo 4 — Valuation Ausente (dados fundamentais)
| Gap | Ticker's | Impacto |
|---|---|---|
| `AI_ENTRY_MISSING` | BPAC11, SANB11 | Ticker fora do pipeline de AI |
| `VALUATION_FLAG_ABSENT` | SUZB3, VALE3 | AI entry existe mas flag=0 (sem valuation) |
| `FAIR_VALUE_MISSING` | BBDC4 | AI entry com flag=1 mas `fair_value` nunca calculado |

### Tipo 5 — Qualidade Fundamental Ausente
| Gap | Ticker's | Impacto |
|---|---|---|
| `FQS_MISSING` | 7 tickers com AI entry | Score nunca calculado em nenhum ticker |

---

## Cobertura por Campo

| Campo | Cobertura | Count/Total |
|---|---|---|
| Preço histórico (cotahist) | ✅ 100% | 9/9 |
| CVM docs (ri_documents) | ⚠️ 56% | 5/9 |
| Valuation disponível (flag) | ✅ 78% | 7/9 |
| Fair value calculado | ⚠️ 44% | 4/9 |
| Valuation method reportado | ❌ 0% | 0/9 |
| Fundamental quality score | ❌ 0% | 0/9 |
| Sector populado | ❌ 0% | 0/9 |
| Company name populado | ❌ 0% | 0/9 |
| Market price populado | ❌ 0% | 0/9 |

---

## Prioridades para S02 (Matriz de Cobertura Operacional)

1. **CRÍTICO — AI entry missing:** BPAC11 e SANB11 não têm entrada em `asset_intelligence_snapshots` — nenhum dado de valuation disponível
2. **CRÍTICO — FQS = 0%:** Score de qualidade fundamental nunca calculado em nenhum ticker
3. **CRÍTICO — Valuation method = 0%:** Nenhum ticker reporta o método usado
4. **CRÍTICO — Discrepância CVM:** BPAC11, SANB11, SUZB3 têm 6.100 registros em `data_source_traceability` mas 0 em `ri_documents` — falha de inserção a investigar
5. **ALTO — CVM docs missing:** VALE3 nem tem trace nem dados; BPAC11, SANB11, SUZB3 com discrepância
6. **ALTO — Sector não populado:** 7 tickers com AI entry mas sem sector
7. **MÉDIO — Fair value gaps:** BBDC4 tem flag=1 mas sem FV; VALE3 e SUZB3 com flag=0 (sem valuation)

---

## Autorização para S02

**AUTORIZADO COM RESSALVAS**

S02 (Matriz de Cobertura Operacional) pode ser executada desde que:

1. ✅ A auditoria de cobertura (S01) foi completada e seus outputs estão disponíveis em `docs/`
2. ✅ A matriz operacional deve priorizar **discrepância CVM (BPAC11, SANB11, SUZB3)** como primeiro bloco — a coleta foi executada mas os dados não chegaram ao banco
3. ✅ A matriz deve tratar **AI entry missing (BPAC11, SANB11)** como pré-condição
4. ✅ VALE3 tem o pior quadro: sem trace, sem CVM, sem AI entry, sem valuation — deve ser tratado como caso de ingestion from scratch
5. ⚠️ Fair values existentes no banco (BBAS3=64.84, ITUB4=73.69, PETR4=81.12, WEGE3=40.16) **devem ser preservados e cross-checked**, não descartados
6. ⚠️ Qualquer cálculo de valuation novo para S02 deve usar a metodologia setorial inferida (`COSIF_BANK`, `COMMODITY_DCF`, `ENERGY_DCF`, `INDUSTRIAL_DCF`) como input, não output inventado
7. ⚠️ VALE3 é caso priority: sem CVM docs E sem trace = pipeline nunca executado para este ticker — ingestion completa antes de qualquer valuation

---

## Relatório S01 — Entrega Final

**a) Quantidade de tickers auditados:** 9 (todos os tickers da watchlist em `config.yaml`)

**b) Cobertura por campo:**

| Campo | Cobertura | Status |
|---|---|---|
| Preço histórico (cotahist) | 9/9 (100%) | ✅ Completo |
| CVM docs (ri_documents) | 5/9 (56%) | ⚠️ 4 tickers sem docs |
| Valuation disponível (flag) | 7/9 (78%) | ⚠️ 2 tickers sem AI entry |
| Fair value | 4/9 (44%) | ⚠️ Presente mas sem market_price/upside |
| Valuation method | 0/9 (0%) | ❌ Nunca populado |
| Fundamental quality score | 0/9 (0%) | ❌ Nunca calculado |
| Sector | 0/9 (0%) | ❌ Nunca populado |
| Company name | 0/9 (0%) | ❌ Nunca populado |
| Market price (AI) | 0/9 (0%) | ❌ Nunca populado (cotahist tem, AI não) |

**c) Arquivos gerados:**

| Arquivo | Tamanho | Conteúdo |
|---|---|---|
| `docs/coverage_audit_20260523.csv` | 10 linhas (header + 9 tickers) | 37 colunas, uma linha por ticker |
| `docs/coverage_audit_README.md` | 207+ linhas | Documentação de colunas, gaps, significado de NULL |

**d) Principais lacunas:**

- **Bloqueador de valuation:** `valuation_method` é NULL em 100% dos tickers — impossibilita saber qual modelo foi aplicado ou deveria ser aplicado
- **Score de qualidade ausente:** `fundamental_quality_score` nunca calculado — sem indicador de robustez dos fundamentos
- **Discrepância operacional:** BPAC11, SANB11, SUZB3 mostram 6.100 registros em traceability mas 0 em `ri_documents` — falha de pipeline
- **VALE3 invisível:** Sem traceabilidade, sem CVM, sem valuation — necessidade de ingestion from scratch
- **Metadados de AI vazios:** company_name, sector, subsector, market_price nunca populados em nenhum ticker

**e) Autorização para S02 — Matriz de Cobertura Operacional:**

✅ **AUTORIZADO COM RESSALVAS** — conforme itens listados acima. O scope de S02 deve cobrir a matriz de ações operacionais para sanar os gaps identificados, priorizando a cadeia de ingestão (CVM → AI → valuation → FQS), com VALE3 como caso de ingestion completa.

---

*Gerado automaticamente via GSD M014-S01. Não modifica banco, frontend, opções, OOS, paper, ou scheduler.*