# Validacao Multi-Cenario de Hipoteses

As hipoteses geradas pela analise de fragilidade devem passar por validacao adicional antes de qualquer observacao recorrente.

## Fluxo

1. Rodar paper trading.
2. Rodar diagnostico de fragilidade.
3. Gerar investigacoes analiticas.
4. Escolher uma hipotese promissora.
5. Rodar validacao OOS/multi-cenario.
6. Avaliar governanca.
7. Manter como hipotese em validacao se houver fragilidade, overfitting ou dados insuficientes.

## Exemplo

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
```

## Relatorio

```powershell
python -m src.scanners.generate_hypothesis_oos_report --run-id 1 --output-dir data/reports/hypothesis_oos
```

## Linguagem

Use sempre:

- hipotese em validacao;
- hipotese promissora;
- observacao recorrente;
- bloqueado por overfitting;
- bloqueado por dados insuficientes;
- nao recomendacao.
