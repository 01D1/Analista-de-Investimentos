# Paper Trading - Motivos de Bloqueio de Hipóteses

## Motivos

O deep dive classifica a hipótese bloqueada com os seguintes motivos:

- `BLOCKED_BY_COST`
- `BLOCKED_BY_SLIPPAGE`
- `BLOCKED_BY_REGIME`
- `BLOCKED_BY_SIGNAL_SOURCE`
- `BLOCKED_BY_ASSET_CONCENTRATION`
- `BLOCKED_BY_LOW_SAMPLE`
- `BLOCKED_BY_OVERFITTING`
- `BLOCKED_BY_NEGATIVE_RETURN`
- `BLOCKED_BY_DRAWDAWN`
- `MIXED_EVIDENCE`
- `NO_CLEAR_BLOCKER`

## Interpretação

Um bloqueio não significa recomendação contrária ao ativo ou à fonte. Ele significa que a hipótese em estudo não sustentou evidência suficiente para observação robusta na amostra simulada.

Exemplo: uma hipótese pode reduzir fragilidade em custo baixo, mas ser bloqueada por custo alto ou slippage alto. Nesse caso, a condição de fragilidade é registrada e a próxima etapa deve investigar parâmetros, cobertura e janelas maiores.

## Relatório

```powershell
python -m src.scanners.generate_hypothesis_deep_dive_report --run-id 1
```

O relatório é apenas simulação, investigação e explicação.

## Bloqueio por Custo/Slippage

Se `LIMIT_SIGNAL_SOURCE` for bloqueada por custo ou slippage, a próxima investigação é a calibração paramétrica:

```powershell
python -m src.scanners.limit_signal_source_calibration --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

Variações que aumentem cost drag, aumentem slippage, destruam retorno ou reduzam demais a amostra permanecem bloqueadas por governança.
