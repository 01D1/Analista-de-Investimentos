# Windows Task Scheduler

## Objetivo

Rodar a rotina diária do scanner quantitativo automaticamente no Windows, mantendo logs locais e sem gravar credenciais no repositório.

## Teste Manual

Antes de criar a tarefa, rode:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/windows/run_daily_quant_routine.ps1
```

O script:

- entra na pasta do projeto;
- ativa `.venv`, se existir;
- roda `daily_quant_routine`;
- salva log em `logs/daily_routine_YYYYMMDD.log`.

Depois da rotina agendada, rode periodicamente a observabilidade para consolidar SLA e alertas recorrentes:

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

## Criar Tarefa

Edite o caminho e execute no PowerShell:

```powershell
schtasks /Create /TN "RadarMacroDailyQuantRoutine" /TR "powershell.exe -ExecutionPolicy Bypass -File \"C:\CAMINHO\PARA\scanner_quant_profit_b3\scripts\windows\run_daily_quant_routine.ps1\"" /SC DAILY /ST 08:30
```

## Consultar

```powershell
schtasks /Query /TN "RadarMacroDailyQuantRoutine" /V /FO LIST
```

## Remover

```powershell
schtasks /Delete /TN "RadarMacroDailyQuantRoutine"
```

## Cuidados

- Confirme que o Python/venv funciona fora do terminal da IDE.
- Não use tokens no `.ps1`.
- Revise logs quando a Mesa Quant mostrar `SUCCESS_WITH_WARNINGS`.
- Revise a aba `SLA & Observabilidade` quando houver fonte `CRITICA`, rotina sem execução recente ou alertas recorrentes.
- O agendamento não altera score, ranking ou filtros.
