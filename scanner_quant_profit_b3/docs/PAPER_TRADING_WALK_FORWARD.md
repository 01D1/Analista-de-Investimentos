# Walk-forward de Regras de Paper Trading

Esta rotina valida regras simuladas de saida fora da amostra. Ela separa treino e teste, escolhe parametros no treino e mede o comportamento no periodo seguinte.

Comando principal:

```powershell
python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv
```

O resultado mostra:

- retorno de treino e teste;
- drawdown de treino e teste;
- profit factor;
- trades por janela;
- flag de overfitting;
- classe de robustez.

Classes:

- `PAPER_WF_ROBUSTO`
- `PAPER_WF_PROMISSOR`
- `PAPER_WF_FRAGIL`
- `PAPER_WF_OVERFIT_PROVAVEL`
- `PAPER_WF_DADOS_INSUFICIENTES`

O walk-forward nao executa ordens reais, nao recomenda compra ou venda e nao aplica parametros automaticamente.

Para ampliar a leitura alem de uma unica fonte ou janela, use a validacao multi-cenario:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
```
