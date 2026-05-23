# Paper Trading - Turnover

## Objetivo

O diagnóstico de turnover mede se a frequência de trades, regras de saída, ativos ou fontes de sinal estão gerando giro excessivo e consumindo a vantagem estatística por custo/slippage.

## Métricas

- trades por dia;
- holding period médio;
- turnover total;
- turnover médio diário;
- turnover por ativo;
- turnover por fonte de sinal;
- turnover por regra de saída;
- razão turnover/retorno.

## Uso

```powershell
python -m src.scanners.cost_slippage_diagnostics --paper-run-id 2 --save-db --csv
```

Resultado é diagnóstico. Não é recomendação e não altera parâmetros.

