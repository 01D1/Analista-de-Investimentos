# Observabilidade Operacional

## Objetivo

A observabilidade operacional consolida saude das fontes, SLA, cobertura de eventos, alertas e execucoes da rotina diaria. Ela foi criada para mostrar se a infraestrutura de dados esta confiavel antes de usar eventos, regimes e governanca como evidencia.

Ela nao executa operacoes, nao altera score, nao altera ranking e nao aplica filtros automaticamente.

## Fluxo Recomendado

```powershell
python -m src.scanners.source_health_check --save-db --csv
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

Depois abra a Mesa Quant:

```powershell
python -m streamlit run src/reports/quant_mesa_dashboard.py --server.headless true
```

## O Que O Comando Calcula

O comando de observabilidade:

- carrega `source_health_checks`;
- calcula SLA por fonte;
- calcula SLA geral;
- carrega `event_coverage_runs` e cobertura por regime;
- calcula tendencia de cobertura;
- carrega `operational_alerts`;
- identifica alertas recorrentes;
- carrega `daily_routine_runs`;
- mede taxa de sucesso da rotina diaria;
- salva snapshots quando `--save-db` esta ativo;
- gera CSVs quando `--csv` esta ativo.

## Saidas CSV

Com `--csv`, sao gerados:

- `source_sla_YYYYMMDD_HHMMSS.csv`;
- `operational_observability_YYYYMMDD_HHMMSS.csv`;
- `alert_analytics_YYYYMMDD_HHMMSS.csv`;
- `coverage_trends_YYYYMMDD_HHMMSS.csv`.

## Alertas De Observabilidade

A observabilidade pode gerar alertas persistidos em `operational_alerts`:

- `SOURCE_SLA_CRITICAL`;
- `SOURCE_SLA_UNSTABLE`;
- `ROUTINE_NOT_RUNNING`;
- `COVERAGE_TREND_WORSENING`;
- `RECURRING_ALERT`.

Esses alertas ajudam a separar problema estatistico de problema operacional. Uma cobertura ruim pode vir de fonte ausente, rotina parada ou historico insuficiente.

## Mesa Quant

A aba `SLA & Observabilidade` mostra:

- SLA por fonte;
- disponibilidade;
- classe de confiabilidade;
- ultimo status;
- dias desde ultimo `OK`;
- historico de checks;
- tendencia de cobertura de eventos;
- cobertura por regime;
- alertas recorrentes;
- saude da rotina diaria;
- snapshots salvos.
- candidatos de retenção;
- contratos de qualidade por fonte;
- relatório semanal consolidado.

## Interpretacao

`OK` indica que as fontes e a rotina estao em condicao adequada para leitura analitica. `WARNING` indica que o sistema roda, mas ha limitacoes de cobertura ou estabilidade. `CRITICAL` indica que alguma fonte ou rotina precisa ser corrigida antes de conclusoes fortes.

## Limites

- A observabilidade mede qualidade operacional, nao qualidade preditiva do score.
- Um SLA bom nao garante cobertura completa de noticias.
- Alertas recorrentes devem ser investigados antes de promover qualquer candidato quantitativo.
- A limpeza real de histórico operacional não roda por padrão; use dry-run para auditoria.
## Auditoria de origem dos dados

Para confirmar cobertura, origem e rastreabilidade das fontes primarias e derivadas:

```bash
python -m src.scanners.data_source_audit --save-db --csv
```
