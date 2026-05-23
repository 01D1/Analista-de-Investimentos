# Paper Trading - Deep Dive de Hipóteses

## Objetivo

O deep dive valida as principais hipóteses em estudo fora da amostra, por fonte de sinal, custo, slippage, regime e ativo. A camada explica por que uma hipótese foi bloqueada e quais condições de fragilidade exigem nova investigação necessária.

Não executa ordens reais, não recomenda compra/venda, não altera score principal, não altera ranking principal e não aplica hipóteses automaticamente.

## Comando

```powershell
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
```

## Saídas

- `hypothesis_deep_oos_results_YYYYMMDD_HHMMSS.csv`
- `hypothesis_block_reasons_YYYYMMDD_HHMMSS.csv`
- `hypothesis_asset_decomposition_YYYYMMDD_HHMMSS.csv`
- `hypothesis_source_decomposition_YYYYMMDD_HHMMSS.csv`

## Governança

Status possíveis:

- `HYPOTHESIS_DEEP_APPROVED_FOR_OBSERVATION`
- `HYPOTHESIS_DEEP_MORE_TESTING_REQUIRED`
- `HYPOTHESIS_DEEP_BLOCKED_COST`
- `HYPOTHESIS_DEEP_BLOCKED_SLIPPAGE`
- `HYPOTHESIS_DEEP_BLOCKED_REGIME`
- `HYPOTHESIS_DEEP_BLOCKED_SOURCE`
- `HYPOTHESIS_DEEP_BLOCKED_ASSET`
- `HYPOTHESIS_DEEP_BLOCKED_OVERFITTING`
- `HYPOTHESIS_DEEP_REJECTED`

A aprovação é apenas observação analítica. Não é recomendação.

## Próxima Calibração

Quando `LIMIT_SIGNAL_SOURCE` for a melhor hipótese em estudo, mas permanecer bloqueada por custo/slippage, rode:

```powershell
python -m src.scanners.limit_signal_source_calibration --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

Essa etapa testa variação paramétrica com controle de custo e controle de slippage antes de qualquer observação recorrente.
