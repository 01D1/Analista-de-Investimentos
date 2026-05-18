# Assistente de Ingestão

O assistente transforma a reconciliação de fontes em um plano operacional guiado, com etapas, comandos sugeridos, validação pós-processamento e comparação antes/depois.

Dry-run padrão:

```bash
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```

Execução controlada:

```bash
python -m src.scanners.ingestion_assistant --sources b3 --execute --confirm --save-db --csv
```

Regras:

- não altera score, ranking ou modelos;
- não apaga dados;
- não executa comandos fora da whitelist;
- execução real exige `--execute --confirm`;
- etapas manuais, como abrir Profit/Excel ou preencher RI, são registradas como pendências.

