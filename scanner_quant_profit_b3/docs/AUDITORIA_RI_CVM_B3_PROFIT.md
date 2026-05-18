# Auditoria RI, CVM, B3 e Profit

## Profit RTD

Verifica o Excel configurado em `config.yaml`, a aba esperada e campos como ativo, ultimo preco, abertura, maxima, minima, volume e negocios.

## B3 COTAHIST

Verifica diretorios raw/processados, arquivos `COTAHIST_A*.ZIP/TXT` e a tabela `cotahist_daily`. Tambem aponta se opcoes nao foram identificadas.

## CVM/IPE

Le os indices `cvm_ipe_index.json` do pipeline qualitativo e consolida documentos, categorias, links e tickers cobertos.

## Sites de RI

Por padrao apenas valida se URLs estao configuradas em `empresas.yaml`. A checagem HTTP e opcional, com request leve e timeout curto:

```bash
python -m src.scanners.data_source_audit --sources ri --check-ri-online --save-db --csv
```

Nao ha crawling agressivo nem dependencia de API paga.

