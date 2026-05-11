# Eventos E Noticias

## Objetivo

A camada de eventos marca sinais quantitativos com contexto externo: resultado, fato relevante, comunicado, macro, juros, cambio, commodity, setor e noticias gerais.

Ela ajuda a separar movimento tecnico sem evento conhecido, movimento tecnico confirmado por evento, movimento possivelmente event-driven, evento contrario ao sinal e contexto macro/setorial.

Essa camada nao faz scraping pesado, nao depende de API paga e nao altera score, ranking, thresholds ou pesos.

## Modelo De Dados

Eventos seguem o formato:

- `event_date`
- `event_datetime`
- `ticker`
- `related_tickers`
- `company_name`
- `event_type`
- `event_source`
- `event_title`
- `event_summary`
- `event_url`
- `sector`
- `macro_tag`
- `commodity_tag`
- `impact_direction`
- `impact_score`
- `confidence`
- `metadata_json`

Tipos aceitos incluem `RESULTADO`, `FATO_RELEVANTE`, `COMUNICADO`, `GUIDANCE`, `DIVIDENDOS`, `MACRO_BRASIL`, `MACRO_EUA`, `JUROS`, `CAMBIO`, `COMMODITY`, `SETORIAL`, `RATING`, `RECOMENDACAO_ANALISTA`, `NOTICIA_GERAL` e `DESCONHECIDO`.

## Importar Eventos

Arquivo exemplo:

```powershell
data/events/market_events_example.csv
```

Comando:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events_example.csv --save-db
```

Na Fase 14, o fluxo recomendado passou a ser o pipeline com conectores e controle de cobertura:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
```

Também é possível combinar fontes locais:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv news_hunter cvm releases --csv-path data/events/market_events_example.csv --save-db --csv
```

Para usar sua base manual:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events.csv --save-db
```

## Link Evento-Sinal

O link considera mesmo ticker, tickers relacionados em `related_tickers`, eventos macro, eventos setoriais, eventos de commodity e janela antes/depois do sinal.

Classificacoes de link:

- `SAME_DAY`
- `BEFORE_SIGNAL`
- `AFTER_SIGNAL`
- `MACRO_CONTEXT`
- `SECTOR_CONTEXT`
- `COMMODITY_CONTEXT`
- `NO_EVENT`

Classificacoes de contexto:

- `TECNICO_SEM_EVENTO`
- `TECNICO_COM_CONFIRMACAO_EVENTO`
- `MOVIMENTO_EVENT_DRIVEN`
- `EVENTO_CONTRA_SINAL`
- `EVENTO_MACRO`
- `EVENTO_SETORIAL`
- `INDEFINIDO`

## Backtest Com Eventos

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
```

Colunas adicionadas aos resultados:

- `has_event`
- `event_type`
- `event_impact_score`
- `event_context_type`
- `days_from_event`
- `event_title`
- `impact_direction`

## Analise Dedicada

Depois de importar eventos e salvar backtests:

```powershell
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

Saidas:

- `data/reports/event_signal_links_YYYYMMDD_HHMMSS.csv`
- `data/reports/event_context_summary_YYYYMMDD_HHMMSS.csv`
- tabela `signal_event_links`
- tabela `event_context_runs`

## Governanca Com Eventos

A governanca usa eventos para evitar conclusoes erradas:

- se o filtro funciona apenas com evento, ele pode ser `CANDIDATO_EVENT_DRIVEN`;
- se ha poucos eventos, fica `BLOQUEADO_EVENTO_INSUFICIENTE`;
- se eventos contrariam os sinais e o resultado piora, fica `BLOQUEADO_EVENTO_CONTRA_SINAL`.
- se a cobertura for fraca, fica `BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE`.

Isso nao aprova nada automaticamente. Apenas classifica a evidencia.

## Controle De Cobertura

O pipeline mede:

- sinais com evento;
- sinais sem evento;
- tickers com e sem cobertura;
- cobertura por mês;
- cobertura por fonte;
- eventos deduplicados.

Qualidades possíveis:

- `COBERTURA_BOA`
- `COBERTURA_MEDIA`
- `COBERTURA_FRACA`
- `COBERTURA_INSUFICIENTE`

## Mesa Quant

A aba `Eventos & Notícias` mostra eventos importados, eventos por tipo/ticker, sinais com evento x sem evento, retorno líquido e hit rate por contexto, links evento-sinal, eventos por regime e governanca por evento.

## Limitacoes

- Eventos sao locais/manuais nesta fase.
- A qualidade depende da cobertura do CSV.
- `impact_score` e `confidence` sao estimativas.
- Datas intraday ainda nao ordenam noticia antes/depois dentro do mesmo pregão.
- A ausencia de evento importado nao significa ausencia real de noticia.
- A camada e analitica e nao representa recomendacao financeira.
