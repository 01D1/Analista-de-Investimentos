# Paper Trading - Custos de Rebalanceamento

## Objetivo

Medir custo e slippage atribuídos a rebalanceamento simulado por ativo, data e motivo.

## Classes

- `REBALANCE_COST_OK`
- `REBALANCE_COST_HIGH`
- `REBALANCE_COST_DOMINATES_EDGE`
- `REBALANCE_DATA_INSUFFICIENT`

## Sugestões Analíticas

- reduzir frequência;
- aplicar diferença mínima de peso;
- agrupar rebalanceamentos;
- bloquear apenas em estudo quando liquidez estiver fraca;
- simular semanal contra mensal.

Nenhuma sugestão é aplicada automaticamente.
