# Pipeline De Eventos

## Inventario De Fontes Encontradas

| Caminho | Tipo de fonte | Formato | Estado | Integracao |
|---|---|---|---|---|
| `../12_PYTHON/news_hunter/banco.db` | Noticias coletadas | SQLite, tabela `noticias` | possui titulo, link, fonte, categoria, datas, conteudo e score | integrado via `news_hunter_connector` |
| `../12_PYTHON/news_hunter/dados/calendario_economico.json` | Calendario macro | JSON | eventos macro locais | integrado via `macro_calendar_connector` |
| `../12_PYTHON/pipeline banco completo/data/qualitative/processed/*/cvm_ipe_index.json` | CVM/IPE | JSON | documentos CVM com categoria, assunto, data e link | integrado via `cvm_connector` |
| `../12_PYTHON/pipeline banco completo/data/qualitative/processed/*/cvm_auto_collect_index.json` | CVM auto collect | JSON | indice de documentos baixados | integrado via `cvm_connector` |
| `../12_PYTHON/pipeline banco completo/data/qualitative/events/*/events.json` | eventos qualitativos extraidos | JSON | eventos por ticker, relevancia, efeito na tese e fonte | integrado via `releases_connector` |
| `../12_PYTHON/pipeline banco completo/data/qualitative/raw/*/auto_cvm/*.txt` | documentos CVM/release brutos | TXT/PDF | base textual rica | preparado para conector futuro mais profundo |
| `../12_PYTHON/pipeline banco completo/data/qualitative/reports/*` | relatórios qualitativos | Markdown | leitura critica de releases e eventos | preparado para leitura de contexto |
| `data/events/market_events_example.csv` | eventos manuais | CSV | exemplo versionável pequeno | integrado via `local_csv_connector` |

Arquivos `main-MacBook Air de Diego.py` e `quality_gate-MacBook Air de Diego.py` retornaram acesso negado no inventário. Eles não foram alterados.

## Fontes Suportadas

O pipeline aceita:

- `csv`
- `manual`
- `news_hunter`
- `cvm`
- `releases`
- `macro_calendar`

Cada conector retorna DataFrame no formato `market_events`.

## Normalizacao

O módulo `src/context/event_normalizer.py` padroniza:

- ticker;
- data;
- tipo de evento;
- fonte;
- titulo;
- direcao de impacto;
- score de impacto;
- confidence.

## Classificacao

O módulo `src/context/event_classifier.py` usa regras simples por palavra-chave. Ele não usa IA externa.

Exemplos:

- lucro acima, recompra, dividendos maiores: `POSITIVO`;
- prejuízo, fraude, renúncia, guidance cortado: `NEGATIVO`;
- comunicado sem viés claro: `NEUTRO` ou `INCERTO`.

## Deduplicacao

Eventos duplicados sao agrupados por:

- ticker;
- data;
- tipo;
- titulo normalizado.

O evento canônico privilegia:

- maior `confidence`;
- fonte mais confiável;
- mais metadados.

URLs e fontes duplicadas sao agregadas em `metadata_json`.

## Cobertura

O módulo `src/context/event_coverage.py` calcula:

- total de sinais;
- sinais com cobertura;
- tickers com e sem eventos;
- cobertura por ticker;
- cobertura por mês;
- cobertura por fonte;
- qualidade da cobertura.
- cobertura por regime, quando `market_regime_daily` estiver disponível.

Classificações:

- `COBERTURA_BOA`
- `COBERTURA_MEDIA`
- `COBERTURA_FRACA`
- `COBERTURA_INSUFICIENTE`

## Comando Operacional

CSV local:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
```

Múltiplas fontes locais:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv news_hunter cvm releases macro_calendar --csv-path data/events/market_events_example.csv --save-db --csv
```

Rotina operacional com configuração e cobertura por regime:

```powershell
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
```

Rotina diária completa com health check e alertas:

```powershell
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
```

Depois:

```powershell
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

## Persistencia

Tabelas usadas:

- `market_events`
- `event_coverage_runs`
- `event_coverage_by_regime`
- `source_health_checks`
- `daily_routine_runs`
- `operational_alerts`
- `signal_event_links`
- `event_context_runs`

Colunas extras de dedupe em `market_events`:

- `duplicate_group_id`
- `is_duplicate`
- `canonical_event_id`
- `coverage_source`
- `normalized_at`

## Governanca

Se a cobertura for `COBERTURA_FRACA` ou `COBERTURA_INSUFICIENTE`, a governança pode classificar como:

- `BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE`
- `BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE`

Assim, um resultado evento x sem evento não vira conclusão forte quando a base ainda é fraca.

## Limitacoes

- Não faz scraping pesado.
- Não acessa APIs pagas.
- A qualidade depende dos arquivos locais disponíveis.
- Deduplicação por título é heurística.
- Conectores CVM/release usam índices e JSONs locais, não baixam documentos.
- A camada não altera score, ranking, filtros ou pesos.
