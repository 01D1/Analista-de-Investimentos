# Paper Trading - Rebalanceamento

O rebalanceamento simulado usa pesos-alvo por risco:

- ativos com maior volatilidade/VaR recebem menor peso;
- ativos bloqueados por risco recebem peso zero;
- há limite máximo por ativo;
- as ordens geradas são simuladas (`BUY`, `REDUCE`, `CLOSE`).

Eventos são persistidos em `paper_rebalance_events`.

O ajuste por regime reduz exposição simulada em cenários laterais, de baixa tendência, alta volatilidade, liquidez fraca ou risco elevado.

