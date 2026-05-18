# Hipoteses de Fragilidade no Paper Trading

As hipoteses sao geradas a partir do diagnostico de fragilidade por ativo, fonte de sinal, custo e drawdown.

## Tipos

- `EXCLUDE_ASSET`: remove um ativo apenas no experimento simulado.
- `LIMIT_ASSET_COST`: investiga se o custo/slippage do ativo explica a fragilidade.
- `LIMIT_ASSET_WEIGHT`: reservado para limites analiticos de peso.
- `EXCLUDE_SIGNAL_SOURCE`: remove uma fonte de sinal apenas na simulacao.
- `LIMIT_SIGNAL_SOURCE`: reduz a amostra de uma fonte em observacao.
- `DISABLE_REBALANCING`: simula a carteira sem rebalanceamento.
- `REDUCE_REBALANCING`: reservado para frequencia menor.
- `INCREASE_MIN_SAMPLE`: exige mais amostra antes de aceitar uma leitura.
- `EXCLUDE_HIGH_FRAGILITY`: remove ativos acima de limite de fragility_score.
- `REDUCE_VOLATILITY_EXPOSURE`: reduz risco_pct/max_positions em experimento.
- `BLOCK_DRAWDOWN_CONTRIBUTOR`: remove contribuidor de drawdown apenas para investigacao.

## Linguagem

Use sempre linguagem analitica:

- hipotese de investigacao;
- experimento simulado;
- fonte em observacao;
- reducao de fragilidade;
- bloqueado por dados insuficientes;
- nao recomendacao.

Nenhuma hipotese deve ser aplicada automaticamente em capital real.
