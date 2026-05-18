# Reconciliação Profit RTD

A reconciliação do Profit compara:

- arquivo Excel configurado;
- data de modificação do Excel;
- última leitura em `profit_snapshots`;
- idade dos dados.

Comando geral:

```bash
python -m src.scanners.data_reconciliation --sources profit --save-db --csv
```

Ações sugeridas quando stale:

- abrir Profit;
- abrir Excel RTD;
- conferir `profit_excel_path` e `profit_sheet_name`;
- rodar `python -m src.scanners.realtime_profit_scanner --once --save-db`;
- usar modo demo apenas como teste de pipeline.

