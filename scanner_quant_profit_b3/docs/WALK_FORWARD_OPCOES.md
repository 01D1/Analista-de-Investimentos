# Walk-forward de Opções

## Objetivo

O walk-forward de opções valida estruturas fora da amostra usando janelas temporais. Ele compara treino e teste, mede degradação, custo, skips, profit factor e janelas positivas.

Essa camada não executa ordens, não recomenda compra ou venda e não promove estruturas a uso operacional. O resultado serve apenas para estudo estatístico.

## Comando

```powershell
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```

Com contexto:

```powershell
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 --structure LONG_CALL --train-months 3 --test-months 1 --with-regimes --with-events --save-db --csv
```

## Métricas

Cada janela registra:

- trades no treino e no teste;
- retorno líquido médio;
- win rate;
- profit factor;
- custo médio;
- percentual de skips;
- janela positiva;
- alerta de overfitting;
- alerta de dados insuficientes.

## Robustez

Classes:

- `OPTIONS_WF_ROBUSTO`;
- `OPTIONS_WF_PROMISSOR`;
- `OPTIONS_WF_FRAGIL`;
- `OPTIONS_WF_OVERFIT_PROVAVEL`;
- `OPTIONS_WF_DADOS_INSUFICIENTES`.

Se a cadeia histórica for insuficiente, o comando retorna diagnóstico e não quebra.

