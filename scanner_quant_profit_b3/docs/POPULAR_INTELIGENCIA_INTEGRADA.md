# Popular Inteligência Integrada Histórica

## Objetivo

Esta rotina gera snapshots históricos de inteligência integrada por ativo e data. Ela consolida camadas disponíveis para ampliar a cobertura de `integrated` em paper trading e validação OOS.

Ela não executa ordens reais, não recomenda compra ou venda, não altera score principal, não muda ranking e não aplica hipótese automaticamente.

## Comando

```powershell
python -m src.scanners.populate_asset_intelligence_history --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 BBAS3 --save-db --csv
```

## Camadas Usadas Quando Disponíveis

- technical;
- quant;
- valuation;
- eventos;
- regimes;
- opções;
- risco.

Quando uma camada não existe para a data, o campo fica vazio e o `data_quality_score` reflete a lacuna. A rotina continua executando para preservar a validação de amostra.

## Saída

- `populated_asset_intelligence_history_YYYYMMDD_HHMMSS.csv`

Os snapshots integrados são fonte de sinal em estudo. Cobertura insuficiente deve bloquear conclusões de robustez, não forçar uma conclusão.

