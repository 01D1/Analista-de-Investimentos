# Rotina De Eventos

## Objetivo

A rotina de eventos transforma a camada manual/CSV em um fluxo operacional repetível. Ela carrega fontes locais, normaliza, classifica, deduplica, persiste eventos e mede cobertura geral e por regime de mercado.

Ela não faz scraping pesado, não depende de API paga e não altera score, ranking, filtros ou pesos.

## Fontes

As fontes ficam em `config/events.yaml`:

- `csv`: arquivo manual pequeno, por padrão `data/events/market_events_example.csv`;
- `news_hunter`: banco SQLite local do News Hunter;
- `macro_calendar`: calendário econômico local em `../12_PYTHON/news_hunter/dados/calendario_economico.json`;
- `cvm`: índices locais CVM/IPE processados;
- `releases`: eventos qualitativos locais extraídos de releases.

Se o arquivo de configuração não existir, o sistema usa defaults seguros e retorna DataFrames vazios para fontes ausentes.

## Calendário Econômico

O conector `macro_calendar_connector` lê o JSON local e cria eventos no formato `market_events`.

Campos preenchidos:

- `event_date`;
- `event_datetime`, quando houver horário;
- `event_source = calendario_economico`;
- `event_title`;
- `event_summary`;
- `event_type`;
- `macro_tag`;
- `impact_direction = INCERTO`;
- `impact_score`;
- `confidence`.

Classificações possíveis incluem `MACRO_BRASIL`, `MACRO_EUA`, `JUROS`, `CAMBIO`, `COMMODITY`, `POLITICO` e `NOTICIA_GERAL`.

## Cobertura Geral

A rotina calcula:

- total de sinais;
- sinais com evento;
- tickers com e sem evento;
- cobertura por mês;
- cobertura por fonte;
- qualidade de cobertura.

Eventos macro sem ticker passam a cobrir sinais da mesma data como contexto de mercado, sem transformar isso em recomendação.

## Cobertura Por Regime

Quando `--with-regimes` é usado, a rotina cruza eventos, sinais e `market_regime_daily`.

São geradas métricas por:

- `primary_regime`;
- `trend_regime`;
- `volatility_regime`;
- `liquidity_regime`;
- `risk_regime`.

A governança deve bloquear conclusões fortes quando um regime tem cobertura `COBERTURA_FRACA` ou `COBERTURA_INSUFICIENTE`.

## Comando Operacional

```powershell
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
```

Para testar sem persistir:

```powershell
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --dry-run --with-regimes
```

## Saídas

CSV em `data/reports`:

- `daily_event_update_events_YYYYMMDD_HHMMSS.csv`;
- `daily_event_coverage_YYYYMMDD_HHMMSS.csv`;
- `daily_event_coverage_by_regime_YYYYMMDD_HHMMSS.csv`.

Tabelas:

- `market_events`;
- `event_coverage_runs`;
- `event_coverage_by_regime`.

## Limitações

- A rotina depende dos arquivos locais existentes.
- A classificação de impacto é heurística.
- Cobertura baixa não prova ausência de notícia.
- Eventos macro cobrem data/regime, mas não explicam automaticamente o movimento de um ativo específico.
- Conclusões event-driven exigem cobertura suficiente por fonte, ticker, mês e regime.
