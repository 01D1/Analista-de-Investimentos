# Mesa Quant

## Objetivo

A Mesa Quant e um dashboard Streamlit para acompanhar backtest historico, calibracao do score, divergencias entre score legado e `score_final`, sinais por ativo e diagnosticos estatisticos do scanner.

Ela nao altera pesos, nao substitui o score legado, nao muda ranking e nao gera recomendacao de investimento. A funcao da mesa e tornar a evidencia estatistica visivel para decisao tecnica futura.

## Como Abrir

```powershell
python -m streamlit run src/reports/quant_mesa_dashboard.py --server.headless true
```

Antes de abrir, gere dados:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo --compare-scores --save-calibration
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv --save-db
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

## Abas Disponiveis

### Visao Geral

Mostra os principais indicadores do ultimo backtest salvo:

- total de sinais analisados;
- ultimo `run_id`;
- quantidade de ativos;
- melhor tipo de sinal;
- melhor faixa de score;
- hit rate D+5;
- retorno medio D+5 e D+10;
- alerta recente de inflacao de score.

Tambem exibe um diagnostico automatico em texto.

### Backtest Historico

Permite selecionar um `run_id` e ver:

- tabela de runs historicos;
- resultados do run selecionado;
- retorno medio por tipo de sinal;
- hit rate por tipo de sinal;
- retorno medio por faixa de score;
- quantidade de sinais por faixa;
- ranking dos melhores sinais historicos.

Quando o backtest líquido está salvo, a aba também mostra:

- alternância entre retorno bruto e líquido;
- impacto de custos no D+5;
- qualidade de execução;
- sinais tradeable e inviáveis;
- comparação entre retorno bruto e líquido.

### Score & Calibracao

Mostra:

- rodadas de calibracao;
- evolucao da media do `score_final`;
- evolucao do percentil 90;
- quantidade de ativos na faixa `80_100`;
- alertas de inflacao;
- ativos da ultima calibracao;
- comparacao score legado x `score_final`;
- distribuicao dos tipos de divergencia.

### Sinais Por Ativo

Permite selecionar um ticker e visualizar:

- historico de sinais;
- `score_final` ao longo do tempo;
- retornos futuros em D+1, D+3, D+5 e D+10;
- taxa de acerto por horizonte;
- melhor e pior sinal;
- media de retorno por tipo de sinal.

### Componentes Do Score

Resume os componentes:

- `score_momentum`;
- `score_tendencia`;
- `score_liquidez`;
- `score_volatilidade`;
- `score_risco`.

Quando houver dados suficientes, exibe relacao dos componentes com retornos futuros. Quando o schema persistido ainda nao tiver componentes no backtest, usa a calibracao como diagnostico descritivo.

### Walk-forward / Fora Da Amostra

Mostra:

- tabela de runs walk-forward;
- tabela de janelas;
- percentual de janelas positivas;
- retorno medio no teste;
- hit rate medio no teste;
- sinais mais robustos;
- buckets mais robustos;
- alerta de overfitting.

Se nao houver dados, a Mesa orienta executar:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
```

### Filtros & Capacidade

Mostra:

- impacto antes/depois dos filtros;
- sinais removidos;
- retorno líquido antes/depois;
- hit rate antes/depois;
- melhores thresholds testados;
- capacidade média por tipo de sinal, faixa de score, classe de capacidade e qualidade do sinal;
- distribuição de `signal_quality`.
- walk-forward dos filtros, com robustez, janelas positivas, concentração e alertas.

Se nao houver dados, a Mesa orienta executar:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv --save-db
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv --save-db
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
```

### Governança Quant

Mostra:

- últimos `governance_reviews`;
- status dos candidatos;
- aprovado ou não aprovado;
- risco;
- confiança;
- motivos favoráveis;
- motivos contrários;
- ações necessárias;
- contagem por status.

Se não houver review salvo, a Mesa orienta executar:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
```

### Regimes De Mercado

Mostra:

- distribuição dos regimes por data;
- último regime classificado;
- retorno líquido por regime;
- hit rate por regime;
- quantidade de sinais por regime;
- filtros ou candidatos restritos/bloqueados por regime.

Comandos:

```powershell
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
```

### Eventos & Noticias

Mostra:

- eventos importados;
- eventos por tipo e ticker;
- sinais com evento x sem evento;
- retorno líquido e hit rate por contexto;
- links evento-sinal;
- eventos por regime;
- governança por evento.

Se nao houver eventos:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events.csv --save-db
```

Fluxo recomendado:

```powershell
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

A aba também mostra qualidade de cobertura, fontes usadas, eventos antes/depois da deduplicação e alerta quando a cobertura é fraca.

### Alertas E Diagnostico

Gera um relatorio com:

- pontos fortes;
- alertas;
- limitacoes;
- proximos passos.

Os alertas incluem score inflado, falta de monotonicidade, amostra insuficiente, divergencia elevada e dados ausentes.

Também há alertas de realismo operacional:

- estratégia perde vantagem após custos;
- muitos sinais inviáveis por liquidez;
- diferença grande entre bruto e líquido;
- custos/slippage estimados relevantes.
- filtros deixam amostra pequena demais;
- retorno líquido segue negativo após filtros;
- capacidade operacional baixa.
- overfitting provável nos filtros;
- concentração excessiva no walk-forward dos filtros.

### Dados Brutos

Mostra e permite baixar CSV de:

- `historical_backtest_runs`;
- `historical_backtest_results`;
- `score_calibration_runs`;
- `score_calibration_assets`.
- `market_events`;
- `signal_event_links`;
- `event_context_runs`.
- `event_coverage_runs`.

## Como Interpretar

Hit rate indica proporcao de sinais positivos em determinado horizonte. Ela nao mede tamanho do ganho, custo, slippage ou risco.

Retorno medio deve ser lido junto com pior retorno, amostra e drawdown aproximado.

Faixas de score devem idealmente mostrar alguma monotonicidade: faixas maiores deveriam performar melhor, ou ao menos piorar menos. Se isso nao ocorrer, o score precisa de nova calibracao.

Divergencias entre score legado e `score_final` nao sao erros automaticamente. Elas apontam onde o modelo novo esta mais rigoroso, mais agressivo ou discordante.

## Fluxo Operacional Recomendado

1. Atualizar dados da B3.
2. Rodar scanner em tempo real com `--compare-scores --save-calibration`.
3. Rodar backtest historico com `--save-db`.
4. Rodar walk-forward com `--save-db`.
5. Rodar filtros ou otimização de thresholds em modo exploratório.
6. Importar eventos locais, quando houver.
7. Rodar backtest/análise com `--with-events`.
8. Abrir a Mesa Quant.
9. Avaliar sinais, scores, calibracao, walk-forward, filtros, capacidade, regimes, eventos e alertas.
10. Decidir proximos testes sem alterar automaticamente os pesos.

## Limitacoes

- A Mesa depende dos dados previamente salvos no SQLite.
- O backtest historico e diario, nao intraday.
- Custos, slippage e spread entram apenas quando o backtest e salvo com `--net`; execucao real de book ainda nao entra.
- A persistencia atual do backtest salva resultados principais; componentes detalhados podem depender da calibracao.
- Filtros e thresholds podem overfitar se a amostra ficar pequena.
- A aba de eventos depende da cobertura local importada por CSV.
- O dashboard e uma ferramenta de pesquisa e auditoria, nao uma recomendacao financeira.
