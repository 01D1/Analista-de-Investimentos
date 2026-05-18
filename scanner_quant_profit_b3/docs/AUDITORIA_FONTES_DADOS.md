# Auditoria de Fontes de Dados

A Fase 26 adiciona uma camada auditavel para verificar se as principais fontes do projeto existem, estao atualizadas, possuem cobertura minima e deixam rastros de origem.

Comando operacional:

```bash
python -m src.scanners.data_source_audit --save-db --csv
```

Auditoria leve de RI online, opcional:

```bash
python -m src.scanners.data_source_audit --sources ri --check-ri-online --save-db --csv
```

Fontes auditadas:

- Profit RTD / Excel: arquivo, aba, colunas, ativos, campos criticos e stale.
- B3 COTAHIST: arquivos raw/processados, registros no banco, tickers, datas e opcoes.
- CVM/IPE: indices locais, documentos, categorias, links e tickers.
- Sites de RI: URLs configuradas e, opcionalmente, resposta HTTP leve.
- News Hunter e eventos: banco local, tabela `noticias`, `market_events`, cobertura e fontes.
- Valuation / Pipeline Banco Completo: planilhas e outputs locais.
- Opcoes: snapshots de cadeia, bid/ask, liquidez, estruturas, backtests e walk-forward.

A auditoria nao altera score, ranking ou filtros. Ela apenas gera diagnostico operacional.

Para reconciliar lacunas detectadas:

```bash
python -m src.scanners.b3_reconciliation --csv --save-db
python -m src.scanners.data_reconciliation --sources b3 options profit ri --save-db --csv
python -m src.scanners.ingestion_assistant --sources b3 profit options ri --dry-run --save-db --csv
```
