# Paper Trading - Diagnóstico de Custos

## Objetivo

Este diagnóstico identifica se custo e slippage são gargalos estruturais do paper trading. A análise decompõe cost drag por ativo, fonte de sinal, regra de saída, regime e holding period.

## Comando

```powershell
python -m src.scanners.cost_slippage_diagnostics --paper-run-id 2 --save-db --csv
python -m src.scanners.fine_cost_diagnostics --paper-run-id 2 --save-db --csv
```

## Leitura

Classes possíveis:

- `COST_DRAG_LOW`
- `COST_DRAG_ACCEPTABLE`
- `COST_DRAG_HIGH`
- `COST_DRAG_DOMINATES_EDGE`
- `INSUFFICIENT_DATA`

## Não recomendação

O diagnóstico não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica parâmetros automaticamente.

## Diagnóstico fino

Use o diagnóstico fino quando `rebalance`, `exit_rule` ou `UNKNOWN` dominarem o cost drag. Ele separa entrada, saída, rebalanceamento, stop, take-profit, trailing stop, fechamento de simulação e metadado ausente.
