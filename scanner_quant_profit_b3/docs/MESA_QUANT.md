# Mesa Quant

## Objetivo

A Mesa Quant e um dashboard Streamlit para acompanhar backtest historico, calibracao do score, divergencias entre score legado e `score_final`, sinais por ativo e diagnosticos estatisticos do scanner.

Ela nao altera pesos, nao substitui o score legado, nao muda ranking e nao gera recomendacao de investimento. A funcao da mesa e tornar a evidencia estatistica visivel para decisao tecnica futura.

Na aba Paper Trading, a seção Cobertura das Fontes de Sinal mostra `quant`, `technical` e `integrated`, com sinais, tickers, dias ativos, regimes, percentual de cobertura e status dos requisitos. Se não houver cobertura, a própria Mesa exibe o comando de checagem.

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
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --train-months 1 --test-months 1 --include-cost-scenarios --include-regimes --signal-sources quant technical integrated --expand-signal-coverage --filter-coverage --save-db --csv
python -m src.scanners.populate_technical_signals --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --dedupe --save-db --csv
python -m src.scanners.populate_asset_intelligence_history --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
python -m src.scanners.signal_coverage_check --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
```

Na aba Paper Trading, a seção `Deep Dive de Hipóteses` mostra governança profunda, motivo principal de bloqueio, sensibilidade a custo, sensibilidade a slippage, fonte de sinal, regime, ativo, explicação e ações necessárias. Se não houver dados, a própria Mesa mostra o comando operacional.

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
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

A aba também mostra qualidade de cobertura, fontes usadas, eventos antes/depois da deduplicação, cobertura por regime e alerta quando a cobertura geral ou por regime é fraca.

### Opções Inteligentes

Mostra:

- runs do scanner inteligente de opções;
- opções analisadas;
- estruturas geradas;
- estruturas aprovadas para estudo;
- estruturas bloqueadas;
- cadeia de opções com tipo, strike, vencimento, DTE, preço, spread, volume, moneyness, liquidez, risco e Greeks aproximados;
- estruturas com débito, perda máxima, lucro máximo, breakeven, payoff ratio, score, status e explicação.
- backtests preliminares de estruturas;
- win rate, retorno líquido médio, profit factor e custo médio;
- resultados por estrutura, ativo-objeto e status.

A aba reforça que `aprovada para estudo` não é recomendação. Se não houver dados, a Mesa orienta executar:

```powershell
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

Para alimentar a seção de backtest:

```powershell
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```

### Operação & Saúde Das Fontes

Mostra:

- último `daily_routine_run`;
- status geral da rotina;
- saúde das fontes;
- fontes `OK`, `WARNING`, `ERROR`, `MISSING`, `STALE` ou `EMPTY`;
- qualidade de cobertura de eventos;
- eventos carregados;
- sinais cobertos;
- alertas operacionais abertos.

Se não houver dados:

```powershell
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
```

### SLA & Observabilidade

Mostra:

- SLA por fonte;
- disponibilidade historica;
- classe de confiabilidade;
- ultimo status e dias desde ultimo `OK`;
- historico de checks;
- tendencia de cobertura de eventos;
- cobertura por regime;
- alertas recorrentes;
- resumo da rotina diaria;
- snapshots de observabilidade.
- últimas limpezas de retenção;
- contratos de qualidade por fonte;
- último relatório semanal.

Se não houver dados:

```powershell
python -m src.scanners.source_health_check --save-db --csv
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

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
- `event_coverage_by_regime`.
- `source_health_checks`;
- `daily_routine_runs`;
- `operational_alerts`.
- `source_sla_snapshots`;
- `operational_observability_snapshots`.
- `retention_cleanup_runs`;
- `retention_cleanup_details`.

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
6. Rodar a rotina de eventos com calendário macro e cobertura por regime.
7. Rodar health check e rotina diária operacional.
8. Rodar observabilidade operacional.
9. Rodar retenção em dry-run e relatório semanal.
10. Rodar backtest/análise com `--with-events`.
11. Rodar análise técnica quantitativa opcional.
12. Abrir a Mesa Quant.
13. Avaliar sinais, scores, calibracao, walk-forward, filtros, capacidade, regimes, eventos, opções, análise técnica, fontes, SLA, retenção e alertas.
14. Decidir proximos testes sem alterar automaticamente os pesos.

## Aba Análise Técnica Quant

A aba `Análise Técnica Quant` mostra:

- ativos analisados;
- setups técnicos detectados;
- setup mais comum;
- score técnico médio;
- tabela de setups com score, confiança, direção, status e explicação;
- snapshots de features técnicas;
- backtest técnico salvo.
- walk-forward técnico;
- thresholds sugeridos;
- deduplicação e redundância removida;
- governança técnica OOS.

Comando sugerido:

```bash
python -m src.scanners.technical_analysis_scanner --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --save-db --csv --with-backtest
python -m src.scanners.technical_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --train-months 3 --test-months 1 --dedupe --optimize-thresholds --save-db --csv
```

## Aba Inteligência Integrada

A aba `Inteligência Integrada` mostra o último snapshot consolidado por ativo:

- score técnico, score quant e upside;
- valuation disponível ou ausente;
- melhor estrutura de opções para estudo;
- regime e contexto de evento;
- score e status integrado;
- governança integrada;
- explicação, razões favoráveis, razões contrárias e ações necessárias.

Comandos sugeridos:

```bash
python -m src.scanners.asset_intelligence_snapshot --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
python -m src.scanners.generate_asset_intelligence_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
python -m src.scanners.generate_asset_change_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence_changes
```

A seção `Histórico & Mudanças` mostra últimos diffs, tipo de mudança material, delta de score, delta de qualidade de dados e evolução por ativo.

## Limitacoes

- A Mesa depende dos dados previamente salvos no SQLite.
- O backtest historico e diario, nao intraday.
- Custos, slippage e spread entram apenas quando o backtest e salvo com `--net`; execucao real de book ainda nao entra.
- A persistencia atual do backtest salva resultados principais; componentes detalhados podem depender da calibracao.
- Filtros e thresholds podem overfitar se a amostra ficar pequena.
- A aba de eventos depende da cobertura local importada por CSV.
- A aba técnica depende de histórico diário e usa setups objetivos para estudo, não calls operacionais.
- A aba integrada depende da presença das camadas salvas; dados ausentes reduzem confiança e não quebram a Mesa.
- O dashboard e uma ferramenta de pesquisa e auditoria, nao uma recomendacao financeira.
## Auditoria de Dados

A Mesa Quant possui uma aba de auditoria para acompanhar confiabilidade geral, score por fonte, status, registros, tickers cobertos e rastreabilidade.

```bash
python -m src.scanners.data_source_audit --save-db --csv
python -m src.scanners.data_source_audit --sources ri --check-ri-online --save-db --csv
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```
## Risco & Volatilidade

A Mesa Quant possui a aba `Risco & Volatilidade` para exibir:

- volatilidade por ativo e regime de volatilidade;
- VaR 95%;
- Expected Shortfall 95%;
- sizing sugerido para estudo;
- fator limitante;
- status de risco;
- stress tests.

Se não houver dados, rode:

```powershell
python -m src.scanners.risk_engine_snapshot --tickers PETR4 VALE3 ITUB4 --capital 100000 --risk-pct 0.005 --save-db --csv
```

Essa aba é diagnóstica e não executa ordens.

## Paper Trading

A aba `Paper Trading` mostra runs de simulação, capital inicial/final, retorno, Sharpe, Sortino, drawdown, ordens simuladas, posições simuladas, exposição, VaR/ES da carteira e governança.
Também mostra eventos de saída, eventos de rebalanceamento, decomposição de P&L e robustez das regras quando gerados.

Se não houver dados:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --save-db --csv
python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
```

Essa aba é apenas simulação. Não executa ordens reais.
