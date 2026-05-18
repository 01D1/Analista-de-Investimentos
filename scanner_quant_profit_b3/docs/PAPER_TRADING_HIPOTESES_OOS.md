# Validacao OOS de Hipoteses de Paper Trading

Esta rotina valida hipoteses promissoras de investigacao em janelas fora da amostra e cenarios de custo, slippage, regime e fonte de sinal.

Ela nao executa ordens reais, nao recomenda compra/venda e nao aplica hipoteses automaticamente.

## Comando

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
```

Com cenarios adicionais:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --include-cost-scenarios --include-regimes --signal-sources quant technical integrated --save-db --csv
```

Com diagnostico de cobertura e filtro de cenarios sem dados uteis:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --train-months 1 --test-months 1 --include-cost-scenarios --include-regimes --signal-sources quant technical integrated --expand-signal-coverage --filter-coverage --save-db --csv
```

Com cobertura mínima obrigatória por fonte:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --require-source-coverage --min-useful-coverage-pct 0.5 --save-db --csv
```

Se uma fonte relevante não tiver população histórica suficiente, ela é excluída do cenário OOS e o run registra `COVERAGE_INSUFFICIENT`. Isso impede que uma conclusão de robustez seja dominada por uma única fonte.

Para ranquear várias hipóteses em múltiplas fontes:

```powershell
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
```

## O Que E Medido

- delta de retorno contra baseline;
- delta de drawdown contra baseline;
- delta de fragility score;
- percentual de cenarios com melhora;
- sensibilidade a custo/slippage;
- instabilidade por regime;
- risco de overfitting;
- governanca para observacao recorrente.
- fontes excluidas por cobertura insuficiente.

## Status de Robustez

- `HYPOTHESIS_ROBUST_FOR_OBSERVATION`
- `HYPOTHESIS_PROMISING`
- `HYPOTHESIS_FRAGILE`
- `HYPOTHESIS_OVERFIT_PROBABLE`
- `HYPOTHESIS_INSUFFICIENT_DATA`
- `COVERAGE_INSUFFICIENT`

## Governanca

Uma hipotese so pode ir para observacao recorrente quando melhora em amostra suficiente, nao depende de custo baixo, nao fica concentrada em um regime e reduz fragilidade media.

Quando a robustez permanece `HYPOTHESIS_FRAGILE`, a governanca retorna `HYPOTHESIS_BLOCKED_NOT_ROBUST`. A hipotese continua em validacao e nao deve ser promovida para observacao recorrente.
