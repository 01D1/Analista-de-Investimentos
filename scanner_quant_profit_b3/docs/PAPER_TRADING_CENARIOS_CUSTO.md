# Cenarios de Custo e Slippage

Os cenarios de custo medem se uma regra simulada continua positiva quando custos e slippage aumentam.

Cenarios padrao:

- `COST_LOW`: custo 5 bps, slippage 2 bps;
- `COST_BASE`: custo 10 bps, slippage 5 bps;
- `COST_HIGH`: custo 20 bps, slippage 10 bps;
- `COST_STRESS`: custo 30 bps, slippage 20 bps.

Classificacoes:

- `COST_ROBUST`: retorno medio positivo e pouca sensibilidade ao custo;
- `COST_SENSITIVE`: retorno positivo, mas cai com custo;
- `COST_FRAGILE`: cenario deixa de ser positivo;
- `COST_INSUFFICIENT_DATA`: amostra insuficiente.

Uso:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --include-cost-scenarios --save-db --csv
```

A leitura e apenas analitica. Um cenario robusto nao e autorizacao operacional.
