# Reconciliação RI

A reconciliação RI lê `empresas.yaml` e lista empresas sem URL de RI configurada.

Comando:

```bash
python -m src.scanners.data_reconciliation --sources ri --save-db --csv
```

Não há busca pesada na web. A rotina apenas gera pendências e templates para preenchimento manual, como:

```yaml
PETR4:
  nome: "Petrobras"
  ri_url: "PREENCHER_URL_RI"
```

