# Alertas Operacionais

## Objetivo

Alertas operacionais transformam falhas silenciosas em registros persistidos. Eles indicam problemas de fonte, cobertura, governança ou execução da rotina diária.

## Tipos

- `SOURCE_MISSING`;
- `SOURCE_STALE`;
- `SOURCE_EMPTY`;
- `COVERAGE_INSUFFICIENT`;
- `REGIME_COVERAGE_INSUFFICIENT`;
- `GOVERNANCE_BLOCKED`;
- `ROUTINE_FAILED`;
- `ROUTINE_WARNING`.
- `SOURCE_SLA_CRITICAL`;
- `SOURCE_SLA_UNSTABLE`;
- `ROUTINE_NOT_RUNNING`;
- `COVERAGE_TREND_WORSENING`;
- `RECURRING_ALERT`.
- `SOURCE_CONTRACT_FAILED`;
- `SOURCE_CONTRACT_WARNING`;
- `RETENTION_CLEANUP_FAILED`;
- `RETENTION_CANDIDATES_HIGH`;
- `ARCHIVE_FAILED`.

## Severidade

- `INFO`: aviso informativo;
- `WARNING`: requer atenção, mas não interrompe a rotina;
- `CRITICAL`: fonte crítica ausente, erro de leitura ou bloqueio forte.

## Persistência

Alertas são salvos na tabela `operational_alerts`.

Cada alerta contém:

- tipo;
- severidade;
- título;
- mensagem;
- fonte;
- data de criação;
- estado resolvido;
- metadados.

## Telegram Opcional

O envio por Telegram é opcional. Para ativar, use variáveis de ambiente:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="..."
```

Se as variáveis não existirem, o sistema apenas retorna `Telegram não configurado` e continua a rotina.

Nunca coloque token em arquivo versionado.

## Observabilidade

Para gerar alertas baseados em SLA, rotina parada, cobertura piorando e recorrencia:

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

Para gerar alertas de contratos e retenção:

```powershell
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
python -m src.scanners.weekly_operational_report --window-days 7 --save-md --csv
```

Para gerar alertas de mudança material na inteligência integrada:

```powershell
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
```

Tipos adicionados:

- `ASSET_STATUS_CHANGED`
- `ASSET_GOVERNANCE_BLOCKED`
- `ASSET_SCORE_DROPPED`
- `ASSET_VALUATION_CHANGED`
- `ASSET_EVENT_RISK_CHANGED`
- `ASSET_REGIME_CHANGED`
- `ASSET_DATA_QUALITY_DROPPED`

Esses alertas não bloqueiam o scanner por conta própria. Eles documentam risco operacional para a Mesa Quant e para a governança.
## Alertas de qualidade de dados

A auditoria de fontes pode gerar alertas como `DATA_SOURCE_MISSING`, `DATA_SOURCE_LOW_RELIABILITY`, `PRIMARY_SOURCE_UNAVAILABLE`, `B3_DATA_STALE`, `CVM_DATA_STALE`, `PROFIT_RTD_STALE`, `OPTIONS_DATA_INSUFFICIENT`, `VALUATION_STALE` e `RI_URL_MISSING`.

```bash
python -m src.scanners.data_source_audit --save-db --csv
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```
