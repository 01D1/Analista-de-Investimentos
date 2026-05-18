# Reconciliação B3

O módulo `src/data_quality/b3_reconciliation.py` compara arquivos `COTAHIST_A*.ZIP/TXT` em `data/raw` com tabelas SQLite como `cotahist_daily`, `b3_quotes` e `market_daily`.

Comando:

```bash
python -m src.scanners.b3_reconciliation --csv --save-db
```

Possíveis issues:

- `RAW_PRESENT_DB_EMPTY`
- `RAW_NEWER_THAN_DB`
- `DB_MISSING_YEAR`
- `OPTIONS_MISSING`
- `INSUFFICIENT_DATA`

Correções sugeridas usam o coletor existente:

```bash
python -m src.collectors.b3_cotahist_collector --year 2026
```

Nada é reprocessado sem `--execute-fixes --confirm`.

