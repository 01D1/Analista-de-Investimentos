# Relatório Semanal Operacional

## Objetivo

O relatório semanal consolida SLA, saúde das fontes, cobertura de eventos, alertas, rotina diária, contratos de qualidade e governança em um Markdown auditável.

Ele serve para revisão operacional, não para recomendação de investimento.

## Comando

```powershell
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

Com governança:

```powershell
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv --include-governance
```

## Conteúdo

O relatório inclui:

1. Sumário executivo.
2. Saúde das fontes.
3. Cobertura de eventos.
4. Contratos de qualidade.
5. Alertas.
6. Rotina diária.
7. Governança.
8. Ações recomendadas.

## Saídas

- Markdown `weekly_operational_report_YYYYMMDD.md`;
- CSVs auxiliares de SLA, contratos e cobertura quando `--csv` é usado.

## Como Usar

Fluxo recomendado:

```powershell
python -m src.scanners.source_health_check --save-db --csv
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

## Limitações

- O relatório depende dos dados persistidos previamente.
- Se a rotina diária não rodou na janela, o relatório sinaliza falta de histórico.
- O relatório não aprova candidatos quantitativos; ele apenas organiza evidências operacionais.
