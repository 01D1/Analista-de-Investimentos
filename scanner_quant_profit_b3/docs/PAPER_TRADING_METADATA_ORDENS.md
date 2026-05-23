# Paper Trading - Metadata de Ordens

## Objetivo

Reduzir `UNKNOWN` em novas simulações, preservando o histórico antigo como evidência diagnóstica.

Campos adicionados para ordens futuras:

- `normalized_order_reason`
- `reason_confidence`
- `cost_bucket`
- `lifecycle_id`
- `parent_signal_id`
- `parent_position_id`
- `is_simulation_end_close`

## Taxonomia

`ENTRY_SIGNAL`, `EXIT_STOP_LOSS`, `EXIT_TAKE_PROFIT`, `EXIT_TRAILING_STOP`, `EXIT_DAILY_LOSS`, `EXIT_WEEKLY_LOSS`, `EXIT_MAX_DRAWDOWN`, `EXIT_TIME`, `EXIT_SIGNAL_REVERSAL`, `EXIT_GOVERNANCE`, `EXIT_SIMULATION_END`, `REBALANCE_RISK`, `REBALANCE_REGIME`, `REBALANCE_WEIGHT`, `REDUCE_POSITION`, `CLOSE_POSITION`, `UNKNOWN`.

## Não recomendação

Metadata serve apenas para diagnóstico e simulação.
