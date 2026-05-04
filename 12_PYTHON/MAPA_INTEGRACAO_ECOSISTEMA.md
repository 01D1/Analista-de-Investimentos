---
title: Mapa de Integracao do Ecossistema Python
tags:
  - python
  - arquitetura
  - integracao
  - intelligence-system
aliases:
  - Mapa Integracao Python
  - Ecossistema Python
---

# Mapa de Integracao do Ecossistema Python

Este documento consolida a leitura dos tres projetos em desenvolvimento e mostra como eles devem se encaixar na espinha dorsal do `intelligence-system`.

Data do mapeamento: 2026-05-03

---

## Visao executiva

O sistema desejado nao e apenas um conjunto de scripts. Ele e uma plataforma local de inteligencia financeira com tres motores especializados:

1. **Mercado**
   - Projeto: `scanner_quant_profit_b3`
   - Papel: captar preco, volume, liquidez, sinais intraday, dados B3 COTAHIST e ranking de acoes/opcoes.

2. **Fundamentalista / Valuation**
   - Projeto: `12_PYTHON/pipeline banco completo`
   - Papel: coletar CVM, macro BCB, mercado, normalizar demonstracoes, projetar, calcular valuation, gerar Excel e historico de recomendacoes.

3. **Noticias / Conteudo**
   - Projeto: `12_PYTHON/news_hunter`
   - Papel: coletar noticias, classificar relevancia, gerar boletim, ler agenda economica e entregar por Telegram.

A base `12_PYTHON/src` ja existe como tentativa de sistema unificado. Ela deve ser tratada como a espinha dorsal:

```text
12_PYTHON/src
  ingestion     -> coleta CVM, B3, precos, noticias
  processing    -> raw -> processed
  analysis      -> metricas, risco, insights
  valuation     -> DCF, configuracao setorial, valuation automatico
  content       -> morning call, posts, teses
  delivery      -> Obsidian, Telegram
  scheduler     -> jobs recorrentes
```

---

## Estado atual por projeto

### 1. Scanner Quant Profit + B3

Caminho:

```text
scanner_quant_profit_b3/
```

Banco principal:

```text
scanner_quant_profit_b3/data/database/scanner_quant.db
```

Tabelas relevantes:

| Tabela | Uso |
|---|---|
| `profit_snapshots` | snapshots do Profit RTD por ativo e horario |
| `cotahist_daily` | historico diario da B3, incluindo acoes e opcoes |
| `realtime_signals` | sinais intraday rankeados pelo scanner |

Saidas relevantes:

| Saida | Uso potencial |
|---|---|
| `data/reports/ranking_*.csv` | ranking operacional para leitura rapida |
| `realtime_signals` | gatilho para alerta e contexto de mercado |
| `cotahist_daily` | base local alternativa ao yfinance |

Papel na integracao:

- Substituir ou complementar o `src/ingestion/b3_scraper.py`, que hoje usa yfinance.
- Alimentar valuation com preco atual, liquidez, volume e volatilidade.
- Alimentar news/contexto com movimentos anormais que merecem explicacao.

---

### 2. Pipeline Banco Completo

Caminho:

```text
12_PYTHON/pipeline banco completo/
```

Banco principal:

```text
12_PYTHON/pipeline banco completo/data/valuation.db
```

Tabela relevante:

| Tabela | Uso |
|---|---|
| `valuations` | historico de runs por ticker, preco justo, upside, score, recomendacao, risco e JSONs completos |

Modulos centrais:

| Modulo | Papel |
|---|---|
| `main.py` | orquestra coleta, normalizacao, valuation, Excel, database e alertas |
| `modules/coletor_cvm.py` | dados CVM |
| `modules/coletor_mercado.py` | precos e beta via yfinance |
| `modules/coletor_macro.py` | Selic, IPCA, DI, TJLP |
| `modules/valuation.py` | motor de valuation |
| `modules/database.py` | persistencia historica em SQLite |
| `modules/alerts.py` | alertas Telegram de valuation |

Integracao real ja encontrada:

- `modules/alerts.py` tenta usar credenciais Telegram do `news_hunter/config.py` como fallback.

Papel na integracao:

- Ser o motor de tese e decisao: transforma dados em valuation, score, recomendacao e alerta.
- Consumir dados do scanner quando houver base melhor que yfinance.
- Consumir noticias classificadas para explicar mudancas de premissa e risco.

---

### 3. News Hunter

Caminho:

```text
12_PYTHON/news_hunter/
```

Banco principal:

```text
12_PYTHON/news_hunter/banco.db
```

Tabelas relevantes:

| Tabela | Uso |
|---|---|
| `noticias` | noticias coletadas, categoria, score, urgencia e resumo |
| `erros_fonte` | falhas por fonte |

Modulos centrais:

| Modulo | Papel |
|---|---|
| `crawler.py` | coleta RSS e salva noticias |
| `classificador.py` | classifica por regras e score |
| `gerar_boletim.py` | gera boletim diario |
| `market_agent.py` | busca indicadores, bolsas, cambio, commodities e agenda |
| `telegram_client.py` | entrega por Telegram |
| `agendador.py` | rotina de envio recorrente |

Papel na integracao:

- Alimentar morning call e content engine.
- Gerar contexto macro para premissas de valuation.
- Explicar movimentos detectados pelo scanner intraday.
- Servir como camada de delivery ja funcional via Telegram.

---

## Base unificada ja existente

Caminho:

```text
12_PYTHON/src/
```

Componentes ja presentes:

| Area | Arquivos observados |
|---|---|
| CLI unica | `src/main.py` |
| Scheduler | `src/scheduler.py` |
| Ingestao | `src/ingestion/cvm_downloader.py`, `src/ingestion/b3_scraper.py` |
| Processamento | `src/processing/pipeline.py`, `src/processing/storage.py` |
| Analise | `src/analysis/metrics_engine.py`, `risk_engine.py`, `insight_engine.py` |
| Valuation | `src/valuation/auto_dcf.py`, `sector_config.py`, `valuation_dcf.py` |
| Conteudo | `src/content/morning_call.py`, `post_generator.py`, `thesis_builder.py` |
| Delivery | `src/delivery/telegram_bot.py`, `obsidian_writer.py` |

Conclusao: a arquitetura alvo ja comecou. O trabalho correto agora e integrar os projetos existentes nela, e nao duplicar tudo.

---

## Conexoes atuais versus conexoes desejadas

| Conexao | Estado atual | Proximo passo |
|---|---|---|
| Pipeline -> News Hunter / Telegram | Parcial: `pipeline/modules/alerts.py` reaproveita credenciais do `news_hunter` | Centralizar delivery em `src/delivery/telegram_bot.py` ou criar adaptador unico |
| Pipeline -> Scanner Quant | Conceitual nos READMEs | Criar leitor de `scanner_quant.db` e usar como fonte de mercado alternativa ao yfinance |
| News Hunter -> Pipeline | Conceitual nos READMEs | Criar leitor de noticias por ticker/setor e anexar contexto ao valuation/insight engine |
| News Hunter -> Scanner Quant | Conceitual nos READMEs | Cruzar noticias urgentes com `realtime_signals` para explicar movimento |
| `12_PYTHON/src` -> Projetos legados | Parcial/indireto | Criar adaptadores em `src/integration/` ou `src/ingestion/legacy_*` |

---

## Modelo recomendado de integracao

Manter os tres projetos como motores especializados, mas criar uma camada de adaptadores na base unificada:

```text
12_PYTHON/src/integration/
  scanner_quant_adapter.py
  news_hunter_adapter.py
  pipeline_valuation_adapter.py
  ecosystem_status.py
```

Responsabilidade dos adaptadores:

- Ler bancos SQLite existentes sem alterar os projetos de origem.
- Expor funcoes pequenas, previsiveis e testaveis.
- Traduzir os dados para formatos comuns usados por `analysis`, `valuation`, `content` e `scheduler`.

Formato mental:

```text
projetos especializados -> adapters -> intelligence-system -> outputs/alertas
```

---

## Primeiras funcoes que devem existir

### `scanner_quant_adapter.py`

```python
get_latest_market_signal(ticker: str) -> dict | None
get_latest_price(ticker: str) -> dict | None
get_options_snapshot(ticker: str) -> list[dict]
get_top_realtime_signals(limit: int = 20) -> list[dict]
```

### `news_hunter_adapter.py`

```python
get_today_news(limit: int = 50) -> list[dict]
get_news_for_ticker(ticker: str, limit: int = 20) -> list[dict]
get_macro_context(limit: int = 20) -> list[dict]
get_urgent_news(limit: int = 20) -> list[dict]
```

### `pipeline_valuation_adapter.py`

```python
get_latest_valuation(ticker: str) -> dict | None
get_valuation_history(ticker: str, limit: int = 10) -> list[dict]
get_current_ranking(limit: int = 20) -> list[dict]
```

### `ecosystem_status.py`

```python
get_ecosystem_status() -> dict
```

Esse status deve responder:

- bancos existem?
- tabelas esperadas existem?
- quantos registros existem?
- ultima coleta de noticias
- ultimo sinal de mercado
- ultimo valuation
- quais integracoes estao saudaveis

---

## Primeiro MVP de sistema integrado

O primeiro MVP nao precisa refatorar tudo. Ele deve apenas ler os tres bancos e produzir uma visao consolidada por ticker:

```text
Ticker: BBDC4

Mercado:
  preco atual
  volume
  sinal intraday
  score do scanner

Noticias:
  noticias urgentes relacionadas
  contexto macro do dia

Valuation:
  preco justo
  upside
  score
  recomendacao
  risco

Saida:
  alerta Telegram se houver combinacao relevante
  nota Markdown no Obsidian
```

Comando desejado:

```powershell
cd "C:\Users\55819\OneDrive - EPEJUD\DIEGO\OBSIDIAN\Analista de Investimentos\12_PYTHON"
python -m src.main status
python -m src.main run-job health_check
python -m src.main ecosystem --ticker BBDC4
```

O comando `ecosystem` ainda precisa ser criado.

---

## Ordem recomendada de implementacao

0. Resolver a camada de qualidade/completude de dados CVM/B3: [[12_PYTHON/PROXIMO_PASSO_AUDITORIA_CVM_B3|Proximo Passo - Auditoria CVM e B3]].
1. Criar `src/integration/` com adaptadores somente leitura.
2. Criar comando CLI `ecosystem --ticker TICKER`.
3. Criar relatorio Markdown consolidado em `14_OUTPUTS/`.
4. Fazer `news_fetcher` do scheduler chamar o `news_hunter` real em vez do stub.
5. Fazer `b3_prices` consultar o `scanner_quant.db` quando existir, usando yfinance como fallback.
6. Fazer `analyze` anexar contexto de noticias e sinais de mercado ao insight engine.
7. Consolidar delivery em uma camada unica de Telegram.

---

## Decisao arquitetural

**Decisao:** preservar os tres projetos atuais como fontes/motores e integrar via adaptadores na base `12_PYTHON/src`.

**Motivo:** eles ja funcionam, tem dados reais, bancos locais, logs e outputs. Reescrever agora aumentaria risco e atrasaria o objetivo. A camada de adaptadores permite evoluir para uma arquitetura unificada sem quebrar o que ja esta operacional.

**Principio:** primeiro ler e conectar; depois migrar internamente apenas o que estiver duplicado ou fragil.
