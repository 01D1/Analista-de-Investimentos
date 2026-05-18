# Popular Sinais Técnicos Históricos

## Objetivo

Esta rotina gera população histórica de features e setups técnicos para estudo. A saída alimenta paper trading, validação OOS e diagnóstico de cobertura.

Ela não executa ordens reais, não recomenda compra ou venda, não altera o score principal e não muda o ranking principal.

## Comando

```powershell
python -m src.scanners.populate_technical_signals --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --dedupe --save-db --csv
```

## O Que A Rotina Faz

1. Carrega histórico diário.
2. Calcula features técnicas.
3. Detecta setups técnicos.
4. Deduplica setups redundantes quando `--dedupe` é usado.
5. Aplica score técnico e governança técnica.
6. Persiste features e setups.
7. Gera CSVs auditáveis.

## Saídas

- `populated_technical_features_YYYYMMDD_HHMMSS.csv`
- `populated_technical_setups_YYYYMMDD_HHMMSS.csv`

Se houver dados insuficientes, a rotina retorna diagnóstico e não quebra o fluxo. O resultado deve ser tratado como fonte de sinal em estudo, não recomendação.

