# Rotina Diária Quant

## Objetivo

A rotina diária orquestra os passos operacionais mínimos para manter a camada de eventos observável:

1. health check das fontes;
2. atualização de eventos;
3. cobertura geral e por regime;
4. análise evento-sinal opcional;
5. governança opcional;
6. geração de alertas;
7. registro da execução.

Ela não envia ordens, não altera score, não muda ranking e não aplica filtros automaticamente.

## Comando Principal

```powershell
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
```

Depois da rotina, gere o snapshot de observabilidade:

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

Rotina semanal recomendada:

```powershell
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

Teste sem persistir:

```powershell
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --dry-run
```

## Persistência

A rotina grava:

- `daily_routine_runs`;
- `source_health_checks`;
- `operational_alerts`;
- tabelas de eventos e cobertura quando `--save-db` estiver ativo.

A observabilidade operacional consolida esses registros em:

- `source_sla_snapshots`;
- `operational_observability_snapshots`.
- `retention_cleanup_runs`;
- `retention_cleanup_details`.

## Status Da Rotina

- `SUCCESS`: rotina executada sem alertas relevantes;
- `SUCCESS_WITH_WARNINGS`: rotina executada, mas há alertas;
- `FAILED`: rotina bloqueada por erro crítico quando `--fail-on-error` está ativo;
- `DRY_RUN`: execução de teste sem persistência.

## Relatório

Com `--csv`, a rotina também cria um relatório Markdown em `data/reports` com resumo de fontes, cobertura e alertas.

## Limitações

- Depende dos arquivos locais configurados.
- Não agenda sozinha; o agendamento fica no Windows Task Scheduler.
- O Telegram é opcional e não deve ser usado como dependência crítica.
- O SLA depende de execuções recorrentes; uma única rotina não forma historico suficiente.
