# Risk Engine Institucional

Camada analítica para estimar risco por ativo sem alterar score principal, ranking ou modelos existentes.

O Risk Engine calcula:

- modelos de volatilidade histórica, EWMA, downside, Parkinson, Garman-Klass e ATR;
- VaR paramétrico, VaR histórico e VaR modificado;
- Expected Shortfall histórico e paramétrico;
- sizing sugerido para estudo por risco fixo, ATR, VaR, liquidez e capital;
- stress tests hipotéticos;
- governança de risco.

Comando operacional:

```powershell
python -m src.scanners.risk_engine_snapshot --tickers PETR4 VALE3 ITUB4 --capital 100000 --risk-pct 0.005 --save-db --csv
```

O resultado é salvo, quando solicitado, nas tabelas `volatility_estimates`, `risk_snapshots`, `var_estimates`, `position_sizing_snapshots`, `stress_test_results` e `risk_governance_reviews`.

Nenhum cálculo aplica posição automaticamente. A saída é diagnóstica e não constitui recomendação financeira.

O paper trading pode consumir `risk_snapshots` para limitar sizing simulado e calcular VaR/ES agregado de carteira simulada.
