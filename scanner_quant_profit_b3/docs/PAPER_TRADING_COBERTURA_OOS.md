# Cobertura OOS para Hipoteses de Paper Trading

Esta camada mede se a validacao OOS de uma hipotese tem dados uteis por janela, cenario, fonte de sinal e regime.

Ela nao cria recomendacao, nao executa ordens e nao aplica hipoteses automaticamente.

## Objetivo

- aumentar janelas OOS disponiveis quando houver historico;
- reduzir cenarios sem dados uteis;
- diagnosticar cobertura minima por regime;
- verificar se `technical` e `integrated` possuem amostra suficiente;
- comparar cobertura antes/depois da expansao conservadora de sinais;
- manter a hipotese bloqueada ate robustez institucional.

## Expansao Conservadora

A expansao usa apenas tabelas ja persistidas:

- sinais quant de backtest historico;
- sinais/setups/features tecnicos persistidos;
- snapshots integrados persistidos.

Se uma fonte nao tiver registros, ela permanece como dados insuficientes.

## Comando Recomendado

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --train-months 1 --test-months 1 --include-cost-scenarios --include-regimes --signal-sources quant technical integrated --expand-signal-coverage --filter-coverage --save-db --csv
```

## Saidas de Cobertura

- `hypothesis_oos_coverage_before_*.csv`
- `hypothesis_oos_coverage_after_*.csv`
- `hypothesis_oos_coverage_comparison_*.csv`
- tabela `paper_hypothesis_oos_coverage`

## Leitura de Governanca

Mesmo com melhor cobertura, uma hipotese so pode ir para observacao recorrente se demonstrar robustez suficiente. Caso contrario, permanece bloqueada por falta de robustez, overfitting, custo, regime ou dados insuficientes.
