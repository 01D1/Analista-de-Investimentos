# Core Quantitativo Fase 2

## Objetivo

Criar uma camada central de calculo quantitativo, composta por funcoes puras, testaveis e independentes de Excel, SQLite e Streamlit. Essa camada deve ser usada gradualmente pelo scanner em tempo real, scanner de opcoes, backtests e dashboards.

## Modulos Criados Nesta Fatia

| Modulo | Responsabilidade |
|---|---|
| `metrics` | Conversao robusta, divisao segura, variacao percentual e metricas intraday |
| `liquidity` | Perfil e score de liquidez com volume, negocios, volume relativo e spread |
| `scoring` | Score composto por momentum, tendencia, liquidez, volatilidade e risco |
| `signals` | Classificacao textual do sinal sem linguagem de recomendacao |
| `options_metrics` | Moneyness, valor intrinseco, valor extrinseco, vencimento, spread e liquidez de opcoes |
| `backtest` | Retornos futuros, MFE, MAE e hit por horizonte |
| `regimes` | Regime simples de tendencia, volatilidade e risco |
| `relative_strength` | Retorno relativo contra benchmark |
| `explanations` | Texto curto e auditavel explicando por que o ativo apareceu no radar |

## Interface Inicial

O core aceita dados em estruturas simples: `dict`, `Series` ou `DataFrame`. Ele retorna dicionarios e DataFrames, sem gravar arquivos nem acessar banco.

Isso permite:

- testar matematica sem depender de Excel ou B3;
- reaproveitar calculos no Streamlit;
- versionar a evolucao do score;
- comparar score antigo e score novo durante uma fase de transicao.

## Score Composto

O score inicial usa os blocos:

- `score_momentum`
- `score_tendencia`
- `score_liquidez`
- `score_volatilidade`
- `score_risco`
- `score_final`

Pesos iniciais:

- 35% momentum;
- 25% tendencia;
- 20% liquidez;
- 10% volatilidade;
- 10% risco.

O score de risco funciona como componente redutor: gaps elevados, range esticado, preco muito perto da maxima depois de grande amplitude e liquidez abaixo do minimo reduzem a nota.

## Classificacao De Sinais

O modulo de sinais ja diferencia:

- `ROMPIMENTO COM VOLUME`;
- `FORCA COM LIQUIDEZ`;
- `ESTICADO / RISCO DE PULLBACK`;
- `FRAQUEZA COM VOLUME`;
- `REVERSAO POSSIVEL`;
- `SEM ASSIMETRIA`;
- `OBSERVAR`;
- `NEUTRO`.

A linguagem e analitica. O modulo nao gera recomendacao de compra ou venda.

## Opcoes

O modulo de opcoes calcula:

- tipo;
- strike;
- dias ate vencimento;
- ITM/ATM/OTM;
- percentual de moneyness;
- valor intrinseco;
- valor extrinseco;
- spread percentual;
- score de liquidez.

Limite atual: Greeks completos dependem de volatilidade implicita observada ou de uma estimativa/modelo. Quando esses dados nao existem, o resultado informa explicitamente a limitacao.

## Backtest Estatistico

O modulo `backtest` nao simula execucao real. Ele mede comportamento historico apos o sinal:

- retorno futuro;
- maxima favoravel;
- maxima adversa;
- acerto por horizonte.

Essa abordagem serve para pesquisa estatistica dos sinais antes de qualquer camada operacional.

## Testes Criados

Os testes cobrem:

- metricas intraday e divisao por zero;
- score de liquidez;
- score composto e penalidade de risco;
- classificacao de rompimento e risco de pullback;
- metricas de opcoes;
- retornos futuros, MFE e MAE;
- regime, forca relativa e explicacao textual.

## Proxima Integracao Recomendada

1. Comparar ranking antigo versus ranking composto por alguns pregoes.
2. Criar tabela canonica `quant_signals` para separar sinais de snapshots operacionais.
3. Migrar dashboard para mostrar os componentes do score.
4. So entao substituir o score antigo.

## Integracao Inicial No Scanner Realtime

O scanner em tempo real agora calcula o score legado e o score composto lado a lado.

Campos legados preservados:

- `score`
- `signal`
- `motivos`

Campos novos:

- `score_final`
- `score_momentum`
- `score_tendencia`
- `score_liquidez`
- `score_volatilidade`
- `score_risco`
- `signal_type`
- `signal_confidence`
- `explanation`

O comando atual segue funcionando. O ranking impresso no terminal ainda usa o score legado para evitar quebra operacional. Os campos novos sao persistidos em `realtime_signals` para comparacao e posterior migracao para uma tabela canonica de sinais.
