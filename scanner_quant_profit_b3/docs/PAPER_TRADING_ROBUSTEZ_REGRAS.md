# Robustez das Regras de Paper Trading

A robustez das regras compara a simulacao simples com a simulacao avancada e avalia se a melhora continua fora da amostra.

Analises disponiveis:

- comparacao simple vs advanced;
- otimizacao exploratoria de parametros;
- walk-forward das regras;
- governanca OOS;
- relatorio Markdown.

Comandos:

```powershell
python -m src.scanners.compare_paper_simulations --simple-run-id 1 --advanced-run-id 2 --save-db --csv
python -m src.scanners.paper_rules_walk_forward --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --train-months 2 --test-months 1 --save-db --csv
python -m src.scanners.generate_paper_rules_report --output-dir data/reports/paper_rules
python -m src.scanners.paper_scenario_validation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-sources quant technical integrated --save-db --csv
```

Governanca OOS:

- `PAPER_OOS_APPROVED_FOR_STUDY`
- `PAPER_OOS_OBSERVATION_ONLY`
- `PAPER_OOS_BLOCKED_OVERFITTING`
- `PAPER_OOS_BLOCKED_DRAWDOWN`
- `PAPER_OOS_BLOCKED_LOW_SAMPLE`
- `PAPER_OOS_BLOCKED_TURNOVER`
- `PAPER_OOS_BLOCKED_NEGATIVE_RETURN`
- `PAPER_OOS_BLOCKED_DATA`

Um status favoravel significa apenas aprovado para estudo. Parametros continuam simulados e nao devem ser tratados como regra operacional.

A validacao multi-cenario adiciona custos, fontes de sinal e regimes para reduzir risco de overfitting.
