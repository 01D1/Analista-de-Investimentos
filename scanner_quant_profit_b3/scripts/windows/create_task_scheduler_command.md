# Windows Task Scheduler

Crie a tarefa somente depois de validar manualmente:

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/windows/run_daily_quant_routine.ps1
```

Exemplo de criação da tarefa diária às 08:30:

```powershell
schtasks /Create /TN "RadarMacroDailyQuantRoutine" /TR "powershell.exe -ExecutionPolicy Bypass -File \"C:\CAMINHO\PARA\scanner_quant_profit_b3\scripts\windows\run_daily_quant_routine.ps1\"" /SC DAILY /ST 08:30
```

Para consultar:

```powershell
schtasks /Query /TN "RadarMacroDailyQuantRoutine" /V /FO LIST
```

Para remover:

```powershell
schtasks /Delete /TN "RadarMacroDailyQuantRoutine"
```

Os logs são salvos em `logs/daily_routine_YYYYMMDD.log`. Não salve tokens em scripts; use variáveis de ambiente para integrações opcionais.
