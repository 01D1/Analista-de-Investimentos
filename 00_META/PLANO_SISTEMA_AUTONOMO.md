# PLANO: Intelligence System Autonomo

> Documento de planejamento para o Claude Code transformar o toolkit manual atual
> num sistema 100% automatizado de analise financeira, com execucao local + nuvem.
>
> Data: 2026-04-18
> Autor: Diego Carvalho + Claude

---

## VISAO GERAL

### Estado Atual
- Toolkit manual: ~25 arquivos .py (modulos + notebooks)
- Execucao: scripts rodados um por um, manualmente
- Dados: coleta da CVM, parsing de DFP/ITR, valuation DCF
- Cobertura: bancos (BBAS3, ITUB4, etc.) + WEGE3
- Sem scheduler, sem banco de dados, sem notificacoes

### Estado Desejado
- Sistema 100% automatico (roda sozinho, notifica quando relevante)
- Qualquer ticker adicionado e processado automaticamente
- Geracao de conteudo com IA (morning call, posts, teses)
- Execucao local + nuvem (Supabase para dados, local para desenvolvimento)
- Pipeline completo: coleta → processamento → analise → conteudo → entrega

---

## ARQUITETURA ALVO

```
┌─────────────────────────────────────────────────────┐
│                    SCHEDULER                         │
│         (APScheduler local + Supabase cron)          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ INGESTOR │→ │ PROCESSOR│→ │ INTELLIGENCE     │  │
│  │          │  │          │  │                  │  │
│  │ - CVM    │  │ - Parser │  │ - Metricas       │  │
│  │ - B3     │  │ - Normal.│  │ - Valuation      │  │
│  │ - News   │  │ - Valid. │  │ - Risk Engine    │  │
│  │ - RI     │  │          │  │ - Insights       │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                      │              │
│                               ┌──────▼──────────┐  │
│                               │ CONTENT ENGINE   │  │
│                               │                  │  │
│                               │ - Morning Call   │  │
│                               │ - Posts          │  │
│                               │ - Teses          │  │
│                               │ - Relatorios     │  │
│                               └──────┬──────────┘  │
│                                      │              │
│                               ┌──────▼──────────┐  │
│                               │ DELIVERY         │  │
│                               │                  │  │
│                               │ - Obsidian vault │  │
│                               │ - Email/Telegram │  │
│                               │ - Dashboard      │  │
│                               └─────────────────┘  │
│                                                     │
├─────────────────────────────────────────────────────┤
│                    STORAGE                           │
│       Supabase (PostgreSQL) + Parquet local          │
└─────────────────────────────────────────────────────┘
```

---

## FASES DE IMPLEMENTACAO

---

### FASE 0 — FUNDACAO (Semana 1)
**Objetivo**: Reorganizar o codigo existente e criar a base do projeto.

#### 0.1 Reestruturar o projeto Python
```
intelligence_system/
├── pyproject.toml              # dependencias e metadata
├── .env.example                # variaveis de ambiente
├── .env                        # (gitignored) chaves reais
├── config/
│   ├── settings.py             # configuracoes centrais (Pydantic Settings)
│   ├── tickers.yaml            # lista de tickers monitorados
│   └── schedules.yaml          # horarios de execucao
├── src/
│   ├── __init__.py
│   ├── main.py                 # ponto de entrada unico
│   ├── scheduler.py            # orquestrador (APScheduler)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── cvm_downloader.py   # (existente — refatorar)
│   │   ├── b3_scraper.py       # NOVO: dados da B3
│   │   ├── news_fetcher.py     # NOVO: coleta de noticias
│   │   └── ri_scraper.py       # NOVO: paginas de RI
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── dfp_parser.py       # (existente — refatorar)
│   │   ├── bank_parser.py      # (existente — refatorar)
│   │   └── news_parser.py      # NOVO: parser de noticias
│   ├── normalization/
│   │   ├── __init__.py
│   │   ├── account_mapper.py   # (existente)
│   │   ├── bank_account_mapper.py # (existente)
│   │   └── news_normalizer.py  # NOVO
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── schemas.py          # (existente)
│   │   ├── bank_schemas.py     # (existente)
│   │   └── reconciler.py       # (existente)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── detect_inconsistencies.py  # (existente)
│   │   ├── earnings_quality.py        # (existente)
│   │   ├── risk_engine.py             # NOVO
│   │   └── insight_engine.py          # NOVO
│   ├── valuation/
│   │   ├── __init__.py
│   │   ├── valuation_dcf.py    # (existente)
│   │   ├── calculate_metrics.py # (existente)
│   │   └── multiples.py        # NOVO: valuation por multiplos
│   ├── content/
│   │   ├── __init__.py
│   │   ├── morning_call.py     # NOVO
│   │   ├── post_generator.py   # NOVO
│   │   ├── thesis_builder.py   # NOVO
│   │   └── llm_client.py       # NOVO: interface com Claude API
│   ├── delivery/
│   │   ├── __init__.py
│   │   ├── obsidian_writer.py  # NOVO: escreve no vault
│   │   ├── telegram_bot.py     # NOVO: notificacoes
│   │   └── email_sender.py     # NOVO: envio por email
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── supabase_client.py  # NOVO: conexao com Supabase
│   │   ├── models.py           # NOVO: SQLAlchemy/Supabase models
│   │   └── parquet_store.py    # NOVO: storage local
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # NOVO: logging padronizado
│       └── retry.py            # NOVO: retry com backoff
├── tests/
│   ├── test_ingestion.py
│   ├── test_parsers.py
│   ├── test_validation.py
│   ├── test_valuation.py
│   └── test_content.py
├── notebooks/                  # (existentes — manter como referencia)
│   ├── 01_wege3_extracao_piloto.py
│   ├── 02_wege3_historico_completo.py
│   └── ...
└── data/
    ├── raw/                    # dados brutos baixados
    ├── processed/              # dados normalizados
    └── output/                 # resultados finais
```

#### 0.2 Configuracao centralizada
Criar `config/settings.py` com Pydantic Settings:
- Chaves de API (CVM, Claude, Supabase, Telegram)
- Paths de dados (raw, processed, output)
- Configuracoes de schedule
- Lista de tickers (carregada de `tickers.yaml`)

#### 0.3 Arquivo tickers.yaml
```yaml
tickers:
  - ticker: BBAS3
    type: bank
    active: true
    priority: high

  - ticker: ITUB4
    type: bank
    active: true
    priority: high

  - ticker: WEGE3
    type: industrial
    active: true
    priority: high

  # Para adicionar novo ticker, basta inserir aqui
  # O sistema faz o resto automaticamente
```

#### 0.4 Logger padronizado
- Loguru com rotacao de arquivos
- Niveis: DEBUG (desenvolvimento), INFO (producao), WARNING (alertas)
- Formato: `[2026-04-18 07:00:00] [INFO] [cvm_downloader] Baixando DFP BBAS3 2025...`

**Entregaveis Fase 0**:
- [ ] Projeto reestruturado com pyproject.toml
- [ ] settings.py funcionando com .env
- [ ] tickers.yaml com todos os ativos atuais
- [ ] Logger configurado
- [ ] Codigo existente migrado para nova estrutura (sem quebrar)
- [ ] `python -m src.main --test` roda sem erro

---

### FASE 1 — INGESTAO INTELIGENTE (Semana 2)
**Objetivo**: Sistema busca dados sozinho para qualquer ticker.

#### 1.1 Refatorar cvm_downloader.py
- Receber ticker como parametro (nao hardcoded)
- Detectar automaticamente quais periodos ja foram baixados
- Baixar apenas dados novos (incremental)
- Salvar em `data/raw/{ticker}/dfp_{ano}.zip`
- Retry automatico com backoff exponencial

#### 1.2 Criar b3_scraper.py
- Coletar preco, volume, cotacoes historicas
- Fonte: API da B3 ou Yahoo Finance (yfinance)
- Atualizacao diaria automatica
- Salvar em Parquet para performance

#### 1.3 Criar news_fetcher.py
- Fontes: RSS feeds (Valor, InfoMoney, Bloomberg)
- Palavras-chave por ticker e setor
- Classificacao automatica (usar tagging do vault)
- Deduplicacao de noticias
- Armazenar em Supabase (tabela `news`)

#### 1.4 Criar ri_scraper.py
- Acessar paginas de RI das empresas
- Detectar novos releases, fatos relevantes, comunicados
- Alertar quando novo documento e publicado

**Entregaveis Fase 1**:
- [ ] `python -m src.main ingest --ticker BBAS3` funciona
- [ ] `python -m src.main ingest --all` processa todos os tickers ativos
- [ ] Dados salvos em raw/ e no Supabase
- [ ] Noticias coletadas e classificadas
- [ ] Log completo de cada execucao

---

### FASE 2 — PROCESSAMENTO AUTOMATICO (Semana 3)
**Objetivo**: Dados brutos sao processados e validados sem intervencao.

#### 2.1 Pipeline automatico
Refatorar `pipeline.py` para:
1. Detectar novos arquivos em `data/raw/`
2. Parsear automaticamente (DFP, ITR, releases)
3. Normalizar contas (mapper + reconciliacao)
4. Validar (BP fecha, DFC consistente, sem duplicatas)
5. Salvar em `data/processed/` e Supabase

#### 2.2 Deteccao de tipo de empresa
- Bancos: usar `bank_parser.py` + `bank_account_mapper.py`
- Empresas gerais: usar `dfp_parser.py` + `account_mapper.py`
- Decisao automatica baseada no campo `type` do `tickers.yaml`

#### 2.3 Alertas de validacao
- Se BP nao fecha: alerta WARNING no log + notificacao
- Se dado duplicado: rejeitar e logar
- Se unidade incorreta: tentar corrigir, senao alertar
- Nunca descartar dados silenciosamente

**Entregaveis Fase 2**:
- [ ] `python -m src.main process --ticker BBAS3` funciona
- [ ] Pipeline completo: raw → processed → validado
- [ ] Dados historicos no Supabase (tabela `financials`)
- [ ] Alertas funcionando para falhas de validacao

---

### FASE 3 — INTELLIGENCE ENGINE (Semana 4-5)
**Objetivo**: Sistema calcula metricas, valuation e detecta riscos automaticamente.

#### 3.1 Calculo de metricas automatico
Para cada ticker processado, calcular:
- Rentabilidade: ROE, ROIC, ROA
- Margens: bruta, EBITDA, liquida, operacional
- Alavancagem: DL/EBITDA, cobertura de juros
- Caixa: FCF, FCF Yield, conversao de caixa
- Multiplos: P/L, P/VP, EV/EBITDA, DY
- Salvar serie historica no Supabase

#### 3.2 Valuation automatico
- DCF automatico com premissas padrao por setor
- Premissas ajustaveis via config
- Cenarios: base, otimista, pessimista
- Sensibilidade: WACC x crescimento
- Recalcular quando novos dados chegam

#### 3.3 Risk Engine
- Detectar riscos automaticamente:
  - Alavancagem crescente
  - Margens comprimindo
  - Governance score baixo
  - Exposicao macro adversa
- Classificar: baixo / moderado / alto / critico
- Vincular a tickers especificos

#### 3.4 Insight Engine
- Cruzar eventos macro (noticias) com dados financeiros
- Exemplo: "Selic subiu → varejo exposto → MGLU3 com DL/EBITDA 4x = risco alto"
- Usar Claude API para gerar insights textuais
- Salvar insights no Supabase (tabela `insights`)

**Entregaveis Fase 3**:
- [ ] `python -m src.main analyze --ticker BBAS3` calcula tudo
- [ ] Dashboard de metricas historicas por ticker
- [ ] Valuation DCF automatico com 3 cenarios
- [ ] Riscos detectados e classificados
- [ ] Insights macro-micro gerados

---

### FASE 4 — CONTENT ENGINE (Semana 6-7)
**Objetivo**: Sistema gera conteudo analitico automaticamente com IA.

#### 4.1 LLM Client (llm_client.py)
- Interface com a API do Claude (Anthropic)
- Prompts carregados do vault (11_PROMPTS/)
- Rate limiting e retry
- Cache de respostas para economia de tokens
- Modelo: claude-sonnet-4-6 para conteudo, claude-haiku-4-5 para classificacao

#### 4.2 Morning Call automatico
- Executar todo dia as 6:30
- Coletar: indices globais, dolar, juros, commodities, noticias
- Gerar texto estruturado (template do vault)
- Salvar no Obsidian vault (14_OUTPUTS/)
- Enviar por Telegram/email

#### 4.3 Post Generator
- Quando novo resultado trimestral e publicado:
  - Extrair dados
  - Calcular metricas
  - Comparar com trimestre anterior e mesmo periodo ano anterior
  - Gerar post analitico (hook + contexto + analise + conclusao)
  - Salvar como rascunho no vault
- Usar template de 14_OUTPUTS/TEMPLATE_POST.md

#### 4.4 Thesis Builder
- Gerar/atualizar tese de investimento quando:
  - Novo resultado trimestral disponivel
  - Evento macro relevante detectado
  - Mudanca significativa em metricas
- Estrutura do vault (15_TEMPLATES/TEMPLATE_TESE_INVESTIMENTO.md)
- Salvar em 03_COMPANIES/{TICKER}/TESE_DE_INVESTIMENTO.md

**Entregaveis Fase 4**:
- [ ] Morning call gerado todo dia automaticamente
- [ ] Posts analiticos gerados a cada resultado trimestral
- [ ] Teses atualizadas automaticamente
- [ ] Todo conteudo salvo no vault do Obsidian
- [ ] Notificacao enviada quando conteudo novo e gerado

---

### FASE 5 — ORQUESTRACAO E DELIVERY (Semana 8)
**Objetivo**: Tudo roda sozinho, no horario certo, com notificacoes.

#### 5.1 Scheduler (scheduler.py)
Usando APScheduler:
```
06:00  — news_fetcher (coletar noticias overnight)
06:30  — morning_call (gerar morning call)
07:00  — b3_scraper (atualizar precos dia anterior)
19:00  — cvm_downloader (checar novos documentos CVM)
19:30  — pipeline (processar dados novos se houver)
20:00  — analyze (recalcular metricas se dados novos)
20:30  — content (gerar posts/teses se analise nova)
Domingo 10:00 — weekly_review (resumo semanal)
```

#### 5.2 Ponto de entrada unico (main.py)
```bash
# Rodar tudo automaticamente (modo daemon)
python -m src.main daemon

# Rodar etapa especifica
python -m src.main ingest --ticker BBAS3
python -m src.main process --all
python -m src.main analyze --ticker WEGE3
python -m src.main content morning-call
python -m src.main content post --ticker ITUB4

# Adicionar novo ticker
python -m src.main add-ticker PETR4 --type oil_gas

# Status do sistema
python -m src.main status
```

#### 5.3 Delivery
- **Obsidian vault**: escrever outputs diretamente no vault
- **Telegram bot**: notificacoes de alertas, morning call, novos posts
- **Email**: resumo semanal opcional
- **Dashboard Streamlit**: visao consolidada (opcional, Fase 6)

#### 5.4 Execucao na nuvem
- Supabase Edge Functions para tarefas leves (news, precos)
- Supabase Cron para triggers periodicos
- Sistema local como "worker" principal para processamento pesado
- Sincronizacao bidirecional via Supabase

#### 5.5 Monitoramento
- Health check a cada hora
- Alerta se algum job falhou
- Log de execucao com duracao e status
- Tabela `job_runs` no Supabase

**Entregaveis Fase 5**:
- [ ] `python -m src.main daemon` roda 24/7
- [ ] Todos os schedules funcionando
- [ ] Telegram bot enviando notificacoes
- [ ] Novo ticker adicionado com um comando
- [ ] Painel de status do sistema

---

### FASE 6 — EXTRAS E POLISH (Semana 9-10, Opcional)
**Objetivo**: Melhorias de qualidade de vida.

#### 6.1 Dashboard Streamlit
- Visao consolidada de todas as empresas
- Graficos de metricas historicas
- Comparativo setorial
- Status do pipeline

#### 6.2 Backtesting
- Comparar valuation passado com preco realizado
- Medir acuracia das teses
- Ajustar premissas automaticamente

#### 6.3 API REST
- Endpoint para consultar dados, metricas, valuations
- Possibilita integracao com outros sistemas
- FastAPI + autenticacao

---

## BANCO DE DADOS (Supabase)

### Tabelas principais

```sql
-- Tickers monitorados
CREATE TABLE tickers (
    ticker TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,          -- bank, industrial, retail, etc.
    sector TEXT,
    active BOOLEAN DEFAULT true,
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Dados financeiros historicos
CREATE TABLE financials (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT REFERENCES tickers(ticker),
    period TEXT,        -- '2025Q4', '2025'
    period_type TEXT,   -- 'quarterly', 'annual'
    account TEXT,       -- 'receita_liquida', 'ebitda', etc.
    value NUMERIC,
    unit TEXT DEFAULT 'BRL_thousands',
    source TEXT,        -- 'CVM_DFP', 'CVM_ITR', 'release'
    ingested_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(ticker, period, account)
);

-- Metricas calculadas
CREATE TABLE metrics (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT REFERENCES tickers(ticker),
    period TEXT,
    metric TEXT,        -- 'roe', 'roic', 'dl_ebitda', etc.
    value NUMERIC,
    calculated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(ticker, period, metric)
);

-- Valuations
CREATE TABLE valuations (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT REFERENCES tickers(ticker),
    method TEXT,        -- 'dcf', 'multiples'
    scenario TEXT,      -- 'base', 'optimistic', 'pessimistic'
    fair_value NUMERIC,
    current_price NUMERIC,
    upside NUMERIC,     -- percentual
    assumptions JSONB,
    calculated_at TIMESTAMPTZ DEFAULT now()
);

-- Noticias
CREATE TABLE news (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    source TEXT,
    url TEXT UNIQUE,
    published_at TIMESTAMPTZ,
    theme TEXT[],       -- ['juros', 'bancos_centrais']
    impact TEXT,        -- 'positive', 'negative', 'neutral'
    sentiment TEXT,
    sectors TEXT[],
    tickers TEXT[],
    summary TEXT,
    ingested_at TIMESTAMPTZ DEFAULT now()
);

-- Insights gerados
CREATE TABLE insights (
    id BIGSERIAL PRIMARY KEY,
    type TEXT,          -- 'macro_micro', 'risk', 'opportunity'
    tickers TEXT[],
    description TEXT,
    source_news_id BIGINT REFERENCES news(id),
    severity TEXT,      -- 'low', 'medium', 'high', 'critical'
    generated_at TIMESTAMPTZ DEFAULT now()
);

-- Conteudo gerado
CREATE TABLE content (
    id BIGSERIAL PRIMARY KEY,
    type TEXT,          -- 'morning_call', 'post', 'thesis'
    ticker TEXT,
    title TEXT,
    body TEXT,
    status TEXT DEFAULT 'draft', -- 'draft', 'reviewed', 'published'
    generated_at TIMESTAMPTZ DEFAULT now()
);

-- Execucoes do pipeline
CREATE TABLE job_runs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT,
    status TEXT,        -- 'running', 'success', 'failed'
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_seconds NUMERIC,
    details JSONB,
    error_message TEXT
);
```

---

## DEPENDENCIAS (pyproject.toml)

```toml
[project]
name = "intelligence-system"
version = "0.1.0"
requires-python = ">=3.11"

[project.dependencies]
# Core
pandas = ">=2.0"
numpy = ">=1.24"
pydantic = ">=2.0"
pydantic-settings = ">=2.0"

# Ingestion
requests = ">=2.31"
httpx = ">=0.27"
yfinance = ">=0.2"
feedparser = ">=6.0"
beautifulsoup4 = ">=4.12"
lxml = ">=4.9"

# Parsing
pdfplumber = ">=0.10"
openpyxl = ">=3.1"

# Storage
supabase = ">=2.0"
pyarrow = ">=14.0"
duckdb = ">=0.10"

# Scheduling
apscheduler = ">=3.10"

# AI / Content
anthropic = ">=0.39"

# Delivery
python-telegram-bot = ">=21.0"

# Observability
loguru = ">=0.7"
rich = ">=13.0"

# Dev
pytest = ">=8.0"
ruff = ">=0.4"
```

---

## COMO USAR ESTE PLANO NO CLAUDE CODE

### Instrucao para colar no Claude Code:

```
Voce e o desenvolvedor principal do Intelligence System.

Seu objetivo e transformar o toolkit manual em 12_PYTHON/ num sistema
100% automatizado seguindo o plano em 00_META/PLANO_SISTEMA_AUTONOMO.md.

Regras:
1. Siga as fases na ordem (0 → 1 → 2 → 3 → 4 → 5)
2. Nao pule etapas — cada fase depende da anterior
3. Mantenha o codigo existente funcionando durante a migracao
4. Use os templates e schemas do vault como referencia
5. Toda funcao deve ter docstring e type hints
6. Testes para cada modulo novo
7. Commits atomicos por funcionalidade

Comece pela Fase 0: reestruturar o projeto.
```

### Para cada sessao do Claude Code:

```
Estou no projeto Intelligence System.
Vault: [caminho do vault]
Plano: 00_META/PLANO_SISTEMA_AUTONOMO.md

Status atual: [Fase X, etapa Y]
Ultimo progresso: [o que foi feito]
Proximo passo: [o que fazer agora]
```

---

## ESTIMATIVA DE TEMPO

| Fase | Descricao | Tempo estimado |
|------|-----------|---------------|
| 0 | Fundacao | 1 semana |
| 1 | Ingestao | 1 semana |
| 2 | Processamento | 1 semana |
| 3 | Intelligence | 2 semanas |
| 4 | Content Engine | 2 semanas |
| 5 | Orquestracao | 1 semana |
| 6 | Extras | 2 semanas (opcional) |
| **Total** | | **8-10 semanas** |

## CUSTOS ESTIMADOS

| Item | Custo mensal |
|------|-------------|
| Supabase (Free tier) | $0 |
| Supabase (Pro, se precisar) | $25 |
| Claude API (conteudo) | $10-30 |
| Telegram Bot | $0 |
| VPS (se usar) | $5-10 |
| **Total estimado** | **$10-65/mes** |

---

## RISCOS DO PROJETO

1. **CVM pode mudar API** — Mitigar: camada de abstracao, fallback para scraping
2. **Rate limiting de APIs** — Mitigar: retry com backoff, cache agressivo
3. **Qualidade do conteudo IA** — Mitigar: revisao humana nos primeiros meses
4. **Custos de API Claude** — Mitigar: usar Haiku para tarefas simples, cache
5. **Dados inconsistentes** — Mitigar: validacao rigorosa, nunca descartar silenciosamente

---

*Este documento deve ser atualizado conforme o projeto avanca.*
*Cada fase completada deve ser marcada no checklist acima.*
