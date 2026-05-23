# Paper Trading - Variantes de Rebalanceamento

## Objetivo

Simular alternativas de rebalanceamento para reduzir cost drag de rebalanceamento simulado.

## Variantes

- `DISABLE_REBALANCE`
- `WEEKLY_REBALANCE`
- `THRESHOLD_REBALANCE_5PCT`
- `THRESHOLD_REBALANCE_10PCT`
- `VOL_ADJUSTED_REBALANCE`
- `REGIME_BLOCKED_REBALANCE`
- `LIQUIDITY_FILTERED_REBALANCE`
- `MAX_REBALANCE_TURNOVER`

## Interpretação

Redução de rebalanceamento pode reduzir custo, mas também pode mudar risco, exposição e drawdown. Por isso a governança bloqueia variantes que melhoram apenas por cortar amostra ou reduzir atividade demais.

## Não recomendação

Todas as variantes são estudos simulados.
