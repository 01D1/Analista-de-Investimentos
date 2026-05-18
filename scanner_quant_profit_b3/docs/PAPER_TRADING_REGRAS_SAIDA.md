# Paper Trading - Regras de Saída

As regras avançadas de saída são simuladas e não enviam ordens reais.

Tipos suportados:

- `FIXED_HOLDING_DAYS`
- `STOP_LOSS_PCT`
- `TAKE_PROFIT_PCT`
- `ATR_STOP`
- `TRAILING_STOP`
- `VAR_STOP`
- `TIME_EXIT`
- `REGIME_EXIT`
- `GOVERNANCE_EXIT`
- `SIGNAL_REVERSAL_EXIT`
- `DAILY_LOSS_EXIT`
- `WEEKLY_LOSS_EXIT`

Exemplo:

```powershell
python -m src.scanners.paper_trading_simulation --start 2026-01-02 --end 2026-04-30 --capital 100000 --signal-source quant --exit-mode advanced --stop-loss-pct 0.03 --take-profit-pct 0.06 --trailing-stop-pct 0.04 --daily-loss-limit-pct 0.02 --enable-rebalancing --save-db --csv
```

Os eventos são persistidos em `paper_exit_events`.

