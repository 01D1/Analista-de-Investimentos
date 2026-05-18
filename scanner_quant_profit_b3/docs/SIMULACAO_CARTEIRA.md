# Simulação de Carteira

A simulação percorre o histórico diário e, para cada data:

1. carrega sinais aprovados para estudo;
2. bloqueia sinais com governança crítica;
3. usa sizing analítico do Risk Engine quando disponível;
4. simula execução com slippage, custo e liquidez;
5. atualiza posições simuladas;
6. marca a mercado;
7. calcula exposição, drawdown, VaR e Expected Shortfall da carteira;
8. registra curva de equity.
9. quando habilitado, registra eventos de saída, rebalanceamento e P&L attribution.

No fim da janela, posições remanescentes são fechadas de forma simulada para materializar P&L do experimento.

Campos importantes:

- `order_status`
- `simulated_execution_price`
- `execution_cost`
- `slippage_cost`
- `market_value`
- `unrealized_pnl`
- `realized_pnl`
- `portfolio_var_95`
- `portfolio_es_95`
- `exit_rule_triggered`
- `target_weight`
- `contribution_pct`
