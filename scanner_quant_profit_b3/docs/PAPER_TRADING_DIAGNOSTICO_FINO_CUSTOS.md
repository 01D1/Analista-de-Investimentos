# Paper Trading - Diagnóstico Fino de Custos

## Objetivo

Separar custo atribuído por entrada, saída, rebalanceamento, stop, take-profit, trailing stop, perda diária/semanal, fechamento de simulação e metadado ausente.

## Comando

```powershell
python -m src.scanners.fine_cost_diagnostics --paper-run-id 2 --save-db --csv
```

## Saídas

- `paper_order_reason_diagnostics`
- `paper_cost_lifecycle`
- `paper_rebalance_cost_diagnostics`
- `paper_exit_rule_cost_diagnostics`
- `paper_unknown_cost_diagnostics`

## Não recomendação

O diagnóstico não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica calibração automaticamente.

## Próximo diagnóstico

Quando saída e rebalanceamento concentrarem o cost drag, rode:

```powershell
python -m src.scanners.cost_reduction_simulation --paper-run-id 2 --save-db --csv
```

O comando testa variantes simuladas, compara antes/depois e aplica governança sem alterar parâmetros operacionais.
