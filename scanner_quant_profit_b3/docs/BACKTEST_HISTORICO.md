# Backtest Historico

## Objetivo

O backtest historico mede como os sinais quantitativos teriam se comportado depois de cada pregao usando precos diarios da B3/COTAHIST ja carregados no SQLite.

Ele nao gera recomendacao de compra ou venda. O objetivo e produzir evidencia estatistica para calibrar o `score_final` antes de qualquer substituicao do score legado.

## Dados Utilizados

O processo usa dados diarios com:

- data do pregao;
- ticker;
- abertura;
- maxima;
- minima;
- fechamento;
- volume financeiro;
- negocios;
- quantidade negociada.

A fonte preferencial e o historico COTAHIST processado. Se houver outra tabela diaria compativel no banco, o loader tenta identifica-la, mas a prioridade operacional continua sendo COTAHIST.

## Metodologia

Para cada ativo e data:

1. calcula features historicas, como retorno, range, gap, volume relativo, medias moveis, volatilidade e ATR;
2. calcula os componentes do score quantitativo;
3. classifica o tipo de sinal;
4. mede retornos futuros em D+1, D+3, D+5 e D+10;
5. calcula maxima favoravel e maxima adversa em janela de 5 pregoes;
6. agrega resultados por tipo de sinal, faixa de score e componentes.

O sinal diario e tratado como conhecido no fechamento do dia. Os retornos futuros usam fechamentos posteriores.

## Comando

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv
```

Com tickers especificos:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --tickers PETR4 VALE3 ITUB4 --csv
```

Para salvar resultados no SQLite:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db
```

Ao salvar no SQLite, os resultados historicos incluem os componentes do score:

- `score_momentum`;
- `score_tendencia`;
- `score_liquidez`;
- `score_volatilidade`;
- `score_risco`;
- `signal_confidence`;
- `explanation`;
- `score_bucket`;
- `market_regime`, quando disponivel.

## Como Interpretar

Taxa de acerto mostra a proporcao de sinais com retorno futuro positivo. Ela nao mede tamanho do ganho, custo, slippage ou risco.

Retorno medio mostra o ganho/perda percentual medio por horizonte. Deve ser lido junto com mediana, melhor retorno, pior retorno e desvio padrao.

Payoff compara ganho medio dos sinais positivos com perda media dos sinais negativos. Um payoff maior que 1 indica que os ganhos medios superaram as perdas medias naquela amostra.

Drawdown e aproximado pela maxima adversa em 5 pregoes. Ele ajuda a avaliar se uma faixa de score entrega retorno, mas exige sofrimento excessivo no caminho.

## Calibracao De Pesos

A calibracao compara:

- correlacao entre `score_final` e retorno futuro;
- correlacao entre componentes e retorno futuro;
- retorno medio por quintil de score;
- monotonicidade do score;
- relacao entre `score_risco` e maxima adversa.

O sistema apenas sugere revisoes. Ele nao altera automaticamente os pesos.

Exemplo de leitura:

> Se `score_momentum` tiver relacao positiva com retorno D+3 e `score_volatilidade` tiver relacao negativa, pode fazer sentido testar mais peso em momentum e menos peso em volatilidade em uma nova rodada, sem trocar o ranking principal.

## Limitacoes

- COTAHIST e diario; nao mede execucao intraday.
- Custos, spread, slippage e friccoes operacionais ainda nao entram no resultado.
- Liquidez historica diaria nao garante capacidade real de execucao.
- Sinais com poucas ocorrencias nao devem orientar mudanca de peso.
- Sobrevivencia de ativos, eventos societarios e ajustes historicos podem distorcer amostras.
- Backtest estatistico nao e recomendacao financeira.

## Uso Correto

Use o relatorio para responder:

- quais tipos de sinal tiveram melhor retorno futuro;
- quais faixas de `score_final` diferenciaram melhor os ativos;
- se o score ficou inflado em faixas altas;
- quais componentes parecem contribuir;
- quais pesos merecem novo teste.

Enquanto nao houver amostra suficiente e validacao fora da amostra, mantenha o score legado e o `score_final` em paralelo.

## Validacao Fora Da Amostra

Depois de salvar o backtest historico, rode:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
```

Essa etapa mede se os sinais e faixas de score que funcionaram no treino continuam funcionando no teste seguinte.

## Backtest Líquido

Para incluir custos, slippage e liquidez mínima:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db --net --cost-bps 10 --slippage-bps 5 --min-volume 5000000
```

Esse modo cria colunas `net_return_1d`, `net_return_3d`, `net_return_5d` e `net_return_10d`, além de `execution_quality`, `liquidity_penalty`, `total_cost_pct`, `total_slippage_pct` e `is_tradeable`.

## Backtest Com Regimes

Para adicionar regimes de mercado ao backtest:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
```

Esse modo adiciona `primary_regime`, `trend_regime`, `volatility_regime`, `liquidity_regime`, `risk_regime` e `regime_confidence`, além de gerar CSV por regime.

## Backtest Com Eventos

Para marcar sinais com eventos locais importados:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events_example.csv --save-db
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --with-events --csv --save-db
```

O backtest adiciona:

- `has_event`;
- `event_type`;
- `event_impact_score`;
- `event_context_type`;
- `days_from_event`;
- `event_title`;
- `impact_direction`.

A análise dedicada pode ser rodada com:

```powershell
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

Essa leitura compara sinais com evento e sem evento, mas nao transforma evento em recomendação.

## Filtros De Qualidade E Thresholds

Depois do backtest líquido, é possível rodar filtros opcionais sem alterar o ranking padrão:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv
```

Também é possível testar combinações de thresholds:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv
```

Esses modos geram relatórios separados de impacto dos filtros e otimização. Eles não substituem o score legado, não mudam pesos e precisam ser avaliados fora da amostra para reduzir risco de overfitting.
