# Reconciliação de Fontes

A reconciliação compara fontes locais, bancos SQLite e artefatos processados para indicar lacunas de ingestão sem alterar sinais, scores, rankings ou modelos.

Comando geral:

```bash
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
```

Execução real de correções permanece bloqueada por padrão. Para B3, uma tentativa controlada exige:

```bash
python -m src.scanners.data_reconciliation --sources b3 --execute-fixes --confirm --save-db --csv
```

Na fase atual, o comando geral apenas diagnostica e sugere comandos. O CLI específico de B3 pode executar o coletor se `--execute-fixes --confirm` for usado.

Para transformar issues em um plano guiado:

```bash
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```
