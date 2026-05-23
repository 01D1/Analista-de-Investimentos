# Paper Trading - Variantes de Regras de Saída

## Objetivo

Simular ajustes em stop loss, take-profit, trailing stop, ATR stop, saída por tempo e fechamento de simulação.

## Variantes

- `WIDER_STOP_LOSS`
- `TIGHTER_STOP_LOSS`
- `WIDER_TAKE_PROFIT`
- `LOWER_TAKE_PROFIT`
- `TRAILING_ONLY`
- `STOP_AND_TRAILING`
- `ATR_STOP_ONLY`
- `NO_TAKE_PROFIT`
- `TIME_EXIT_ONLY`
- `DELAYED_STOP_ACTIVATION`
- `NO_SIMULATION_END_CLOSE`

## Interpretação

Uma regra de saída simulada pode reduzir custo ao diminuir saídas, mas o trade-off precisa ser medido em retorno, drawdown, turnover e amostra. Nenhuma variante aprovada em simulação vira parâmetro operacional automaticamente.

## Não recomendação

Este material é diagnóstico. Não recomenda compra/venda e não altera o comportamento do scanner principal.
