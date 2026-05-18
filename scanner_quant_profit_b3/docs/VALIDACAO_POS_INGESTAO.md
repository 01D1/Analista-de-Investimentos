# Validação Pós-ingestão

Após o plano de ingestão, a rotina valida:

- B3: registros, anos disponíveis, tickers e opções;
- Profit RTD: último snapshot, idade da leitura, campos críticos;
- Opções: snapshots, underlyings, vencimentos, strikes, bid/ask e liquidez;
- RI: empresas com ou sem `ri_url`.

Os resultados são salvos em `post_ingestion_validation_results` e comparados com a auditoria inicial quando `--compare-before-after` estiver ativo.

