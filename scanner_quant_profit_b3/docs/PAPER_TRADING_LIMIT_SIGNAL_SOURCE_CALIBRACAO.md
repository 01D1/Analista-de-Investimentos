# Paper Trading - Calibração LIMIT_SIGNAL_SOURCE

## Comando

```powershell
python -m src.scanners.limit_signal_source_calibration --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

Com cenários adicionais:

```powershell
python -m src.scanners.limit_signal_source_calibration --start 2026-01-02 --end 2026-04-30 --include-cost-scenarios --include-slippage-scenarios --include-regimes --save-db --csv
```

## O Que É Medido

- delta de retorno;
- delta de drawdown;
- delta de fragilidade;
- delta de cost drag;
- delta de slippage;
- percentual de sinais removidos;
- cobertura útil;
- sensibilidade a custo;
- sensibilidade a slippage;
- risco de overfitting;
- status de governança.

## Relatório

```powershell
python -m src.scanners.generate_limit_signal_source_report --run-id 1
```

## Leitura Correta

Uma variação aprovada significa apenas `LIMIT_SOURCE_APPROVED_FOR_OBSERVATION`. Isso autoriza observação recorrente em simulação, não aplicação operacional.

