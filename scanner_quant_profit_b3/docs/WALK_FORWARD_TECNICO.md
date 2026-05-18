# Walk-forward Técnico

O walk-forward técnico valida setups fora da amostra. A ideia é separar padrões que parecem bons dentro do período de treino daqueles que continuam funcionando em janelas futuras.

## Quando usar

Use após gerar features e setups técnicos, especialmente quando houver muitos sinais ou retorno médio fraco no backtest exploratório.

## Comando

```bash
python -m src.scanners.technical_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --train-months 3 --test-months 1 --dedupe --optimize-thresholds --save-db --csv
```

## Interpretação

- `TECH_WF_ROBUSTO`: janelas positivas, retorno OOS positivo e hit rate adequado.
- `TECH_WF_PROMISSOR`: resultado positivo, mas ainda limitado.
- `TECH_WF_FRAGIL`: pouca evidência fora da amostra.
- `TECH_WF_OVERFIT_PROVAVEL`: treino bom e teste ruim.
- `TECH_WF_DADOS_INSUFICIENTES`: poucas janelas ou poucos sinais.

O resultado não altera o score principal e não promove setup a operação.

