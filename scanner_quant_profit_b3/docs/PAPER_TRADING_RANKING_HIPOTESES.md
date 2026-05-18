# Paper Trading - Ranking de Hipóteses

## Objetivo

O ranking multi-fonte compara hipóteses em estudo usando `quant`, `technical` e `integrated`. A meta é identificar hipóteses que reduzem fragilidade sem destruir retorno.

Esta camada não executa ordens reais, não recomenda compra/venda, não altera score principal, não altera ranking principal e não aplica hipóteses automaticamente.

## Comando

```powershell
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
```

Com cenários adicionais:

```powershell
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --include-cost-scenarios --include-regimes --save-db --csv
```

## O Que É Medido

- consistência de melhora;
- delta de retorno;
- delta de drawdown;
- delta de fragilidade;
- sensibilidade a custo;
- diversidade de fontes;
- estabilidade por regime;
- penalidade de overfitting;
- penalidade de cobertura.

## Classes

- `HYPOTHESIS_ROBUST`
- `HYPOTHESIS_PROMISING`
- `HYPOTHESIS_OBSERVATION_ONLY`
- `HYPOTHESIS_FRAGILE`
- `HYPOTHESIS_REJECTED`
- `HYPOTHESIS_INSUFFICIENT_DATA`

Uma hipótese robusta para observação não é recomendação. Ela apenas merece acompanhamento recorrente em simulação.

## Deep Dive das Melhores Hipóteses

Depois de salvar um ranking, aprofunde as hipóteses prioritárias:

```powershell
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
```

O deep dive testa custo, slippage, regime, fonte de sinal e ativo. A saída principal é o motivo de bloqueio ou a liberação para observação analítica. Continua sendo não recomendação.
