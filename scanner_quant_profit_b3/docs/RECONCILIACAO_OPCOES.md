# Reconciliação de Opções

A reconciliação de opções verifica:

- `options_chain_snapshots`;
- opções vindas do `cotahist_daily`;
- `option_structure_candidates`;
- `option_scanner_runs`;
- cobertura bid/ask;
- volume/negócios;
- underlyings, vencimentos e strikes.

Comando:

```bash
python -m src.scanners.data_reconciliation --sources options --save-db --csv
```

Comandos sugeridos:

```bash
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.options_intelligence_scanner --save-db --csv
```

