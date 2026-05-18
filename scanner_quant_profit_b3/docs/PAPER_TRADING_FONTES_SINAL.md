# Fontes de Sinal no Paper Trading

A validacao por fonte compara sinais `quant`, `technical` e `integrated` dentro da carteira simulada.

Metricas:

- retorno medio;
- drawdown medio;
- win rate;
- profit factor;
- turnover;
- trades;
- percentual de periodos positivos;
- classe de robustez.

Classes:

- `SIGNAL_SOURCE_PROMISSOR`
- `SIGNAL_SOURCE_FRAGIL`
- `SIGNAL_SOURCE_OVERFIT_PROVAVEL`
- `SIGNAL_SOURCE_DADOS_INSUFICIENTES`

Comando:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
```

Fonte de sinal em observacao nao e recomendacao de compra ou venda. A comparacao serve para diagnostico de robustez.
