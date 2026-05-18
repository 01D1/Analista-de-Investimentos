# Ingestão B3, Profit e Opções

## B3

Comando sugerido pelo plano:

```bash
python -m src.collectors.b3_cotahist_collector --year 2026
```

## Profit RTD

Ação manual antes do comando:

- abrir Profit;
- abrir Excel RTD;
- confirmar o caminho em `config.yaml`.

Depois:

```bash
python -m src.scanners.realtime_profit_scanner --once --save-db
```

## Opções

```bash
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.options_intelligence_scanner --save-db --csv
```

Essas rotinas alimentam dados para estudo e auditoria. Não executam ordens e não constituem recomendação.

