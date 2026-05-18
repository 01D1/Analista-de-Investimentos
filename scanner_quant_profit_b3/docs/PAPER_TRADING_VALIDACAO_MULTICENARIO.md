# Validacao Multi-Cenario do Paper Trading

A validacao multi-cenario testa a carteira simulada em diferentes periodos, fontes de sinal, custos, slippage e regimes. O objetivo e separar melhora pontual de robustez observada.

Comando principal:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
```

Com custos e regimes:

```powershell
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --include-cost-scenarios --include-regimes --save-db --csv
```

A rotina avalia:

- periodos moveis;
- cenarios baseline e advanced;
- fontes de sinal em observacao;
- custos e slippage;
- drawdown, retorno, win rate e profit factor;
- governanca multi-cenario.

Status de governanca:

- `PAPER_SCENARIO_ROBUST_FOR_STUDY`
- `PAPER_SCENARIO_PROMISING`
- `PAPER_SCENARIO_OBSERVATION_ONLY`
- `PAPER_SCENARIO_BLOCKED_OVERFITTING`
- `PAPER_SCENARIO_BLOCKED_COST_SENSITIVE`
- `PAPER_SCENARIO_BLOCKED_REGIME_FRAGILE`
- `PAPER_SCENARIO_BLOCKED_LOW_SAMPLE`
- `PAPER_SCENARIO_BLOCKED_NEGATIVE_RETURN`

A validacao nao executa ordens reais e nao aplica parametros automaticamente.

Quando a governanca multi-cenario bloquear por custo, drawdown ou fonte fragil, rode:

```powershell
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
```

Esse diagnostico ajuda a localizar ativos, fontes e custos que explicam a fragilidade detectada.
