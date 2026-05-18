# Backtest de Estruturas de Opções

## Objetivo

O backtest preliminar de estruturas de opções simula entradas e saídas usando snapshots históricos de cadeia. Ele considera bid/ask, vencimento econômico, custos por perna, slippage por perna e liquidez mínima.

Ele não executa ordens, não faz recomendação financeira e não promove estruturas a uso operacional.

## Comando

```powershell
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
```

Parâmetros úteis:

```powershell
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 --structure LONG_CALL --min-dte 7 --max-dte 90 --target-moneyness ATM --min-liquidity-score 50 --max-spread-pct 15 --holding-days 5 --cost-bps 10 --slippage-bps 5 --save-db --csv
```

## Saídas

Cada resultado contém:

- data de entrada e saída;
- ativo-objeto;
- tipo de estrutura;
- vencimento;
- DTE de entrada e saída;
- pernas em JSON;
- débito ou crédito de entrada;
- valor de saída;
- P&L bruto;
- P&L líquido;
- retorno líquido;
- perda máxima;
- retorno sobre risco;
- motivo de saída;
- custos, slippage e spread;
- qualidade de execução;
- status.

## Status

Os principais status são:

- `COMPLETED`;
- `SKIPPED_NO_LIQUIDITY`;
- `SKIPPED_MISSING_DATA`;
- `SKIPPED_INVALID_STRUCTURE`;
- `OPEN`;
- `EXPIRED`.

Quando não há histórico suficiente, o run é salvo como `INSUFFICIENT_DATA`.

## Interpretação

O relatório é preliminar. Resultados dependem da qualidade da cadeia histórica, bid/ask e premissas de execução. Um resultado positivo não deve ser tratado como recomendação nem como candidato operacional sem walk-forward e governança adicional.

## Validação Fora Da Amostra

A camada inclui avaliação básica treino/teste por data para comparar retorno líquido médio, win rate e degradação entre períodos. Essa análise é apenas diagnóstico estatístico inicial. Para qualquer conclusão forte, ainda será necessário walk-forward de estruturas com múltiplos regimes, eventos e janelas.

Comando de walk-forward:

```powershell
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```
