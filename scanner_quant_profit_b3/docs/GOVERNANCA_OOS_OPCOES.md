# Governança OOS de Opções

## Objetivo

A governança OOS de opções classifica resultados de walk-forward de estruturas. Ela impede interpretação forte quando há poucos dados, poucos trades, custo alto, baixa liquidez ou indício de overfitting.

Ela não aprova operação. `APPROVED_FOR_STUDY` significa apenas estrutura para estudo.

## Status

- `OPTIONS_OOS_APPROVED_FOR_STUDY`;
- `OPTIONS_OOS_OBSERVATION_ONLY`;
- `OPTIONS_OOS_BLOCKED_OVERFITTING`;
- `OPTIONS_OOS_BLOCKED_INSUFFICIENT_DATA`;
- `OPTIONS_OOS_BLOCKED_EXECUTION`;
- `OPTIONS_OOS_BLOCKED_LOW_LIQUIDITY`;
- `OPTIONS_OOS_BLOCKED_COST_DRAG`.

## Critérios

Uma estrutura só pode ser classificada como estudo promissor fora da amostra quando:

- há janelas suficientes;
- janelas positivas são pelo menos 60%;
- retorno líquido médio de teste é positivo;
- win rate de teste é adequado;
- há trades suficientes no teste;
- custo médio não elimina a vantagem;
- não há overfitting relevante.

## Interpretação

Estruturas bloqueadas por dados devem aguardar histórico de cadeia melhor. Estruturas bloqueadas por execução indicam que spread, slippage ou liquidez inviabilizam a leitura estatística.

