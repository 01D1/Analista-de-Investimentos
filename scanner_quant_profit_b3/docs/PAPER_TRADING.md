# Paper Trading

Camada de simulação de carteira que usa sinais, governança, sizing analítico, risco e custos para gerar ordens simuladas.

Comando:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --save-db --csv
```

O paper trading:

- não executa ordens reais;
- não altera score principal;
- não altera ranking principal;
- não aplica sizing automaticamente em capital real;
- gera apenas carteira simulada, ordens simuladas, posições simuladas, curva de equity e governança.
- suporta regras avançadas de saída, rebalanceamento simulado e decomposição de P&L.

Tabelas:

- `paper_simulation_runs`
- `paper_orders`
- `paper_positions`
- `paper_equity_curve`
- `paper_exit_events`
- `paper_rebalance_events`
- `paper_pnl_attribution`

Comando avançado:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --exit-mode advanced --stop-loss-pct 0.03 --take-profit-pct 0.06 --trailing-stop-pct 0.04 --daily-loss-limit-pct 0.02 --enable-rebalancing --save-db --csv
```

Robustez das regras:

```powershell
python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv
```

A comparacao simple vs advanced e o walk-forward servem para investigar se a melhora das regras simuladas persiste fora da amostra. Parametros continuam em estudo.

Validacao multi-cenario:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
```

Essa rotina compara periodos, fontes de sinal, custos e regimes para separar robustez real de overfitting.

Diagnóstico de fragilidade:

```powershell
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
```

O diagnóstico decompoe contribuição negativa por ativo, fonte de sinal, custo/slippage e drawdown. Tudo permanece como análise de simulação.

Investigações analíticas:

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
```

Essa etapa transforma fragilidades em hipóteses simuladas e compara antes/depois. Nenhuma exclusão, limite ou parâmetro é aplicado automaticamente.
