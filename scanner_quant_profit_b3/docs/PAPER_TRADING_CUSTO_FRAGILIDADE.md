# Fragilidade de Custo e Slippage

A fragilidade de custo mede quanto taxas simuladas e slippage consomem do P&L da carteira simulada.

Classificacoes:

- `COST_ROBUST`
- `COST_SENSITIVE`
- `COST_FRAGILE`
- `COST_DOMINATED`

Indicadores:

- custo transacional total;
- slippage total;
- custo sobre P&L;
- ativo que deixa de contribuir depois de custos;
- cenário em que o edge desaparece.

Comando:

```powershell
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --scenario-run-id 1 --save-db --csv
```

A analise e simulada e nao altera qualquer parametro automaticamente.
