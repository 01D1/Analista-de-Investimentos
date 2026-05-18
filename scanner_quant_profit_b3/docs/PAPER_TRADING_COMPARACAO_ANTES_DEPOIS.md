# Comparacao Antes/Depois das Investigacoes

A comparacao mede se um experimento simulado melhora ou piora a carteira em relacao ao paper run base.

## Metricas

- retorno total;
- max drawdown;
- profit factor;
- win rate;
- trades_count;
- turnover;
- fragility_score;
- cost_drag;
- governanca.

## Classificacoes

- `INVESTIGATION_IMPROVED`
- `INVESTIGATION_MIXED`
- `INVESTIGATION_NO_IMPROVEMENT`
- `INVESTIGATION_WORSE`
- `INVESTIGATION_INSUFFICIENT_DATA`

## Cuidados

Melhoras com pouca amostra podem indicar overfitting. Melhoras por exclusao de muitos trades devem ser reavaliadas em validacao multi-cenario.

Relatorio:

```powershell
python -m src.scanners.generate_paper_investigation_report --run-id 1 --output-dir data/reports/paper_investigations
```

Validacao OOS da melhor hipotese:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
```
