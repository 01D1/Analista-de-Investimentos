# Otimizacao de Saidas no Paper Trading

A otimizacao de saidas faz grid search de parametros simulados para estudar sensibilidade das regras.

Parametros avaliados:

- stop loss percentual;
- take-profit percentual;
- trailing stop;
- limite de perda diaria;
- multiplicador de ATR;
- numero maximo de posicoes;
- risco por posicao.

Metricas:

- retorno total;
- drawdown maximo;
- Sharpe;
- Sortino;
- win rate;
- profit factor;
- trades;
- turnover;
- risco de overfitting.

A otimizacao e exploratoria. Ela nao altera o score principal, nao altera ranking, nao executa ordens e nao aplica parametros automaticamente.
