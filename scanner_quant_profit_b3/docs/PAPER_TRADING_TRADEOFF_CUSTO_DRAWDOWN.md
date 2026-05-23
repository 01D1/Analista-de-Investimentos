# Paper Trading - Trade-off Custo e Drawdown

## Objetivo

Evitar que a redução de custo seja interpretada isoladamente. Uma variante pode cortar custo e ainda piorar drawdown, retorno ou qualidade da amostra.

## Métricas

- `cost_reduction_pct`
- `return_delta`
- `drawdown_delta`
- `turnover_delta`
- `cost_reduction_to_return_loss`
- `cost_reduction_to_drawdown_penalty`
- `tradeoff_score`
- `governance_status`

## Classes

- `EFFICIENT_TRADEOFF`
- `ACCEPTABLE_TRADEOFF`
- `MIXED_TRADEOFF`
- `BAD_TRADEOFF`
- `INSUFFICIENT_DATA`

## Não recomendação

O score de trade-off serve para priorizar novas validações fora da amostra, não para aplicar parâmetros.
