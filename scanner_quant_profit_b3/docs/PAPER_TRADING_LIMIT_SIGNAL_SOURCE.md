# Paper Trading - LIMIT_SIGNAL_SOURCE

## Objetivo

`LIMIT_SIGNAL_SOURCE` é uma hipótese em estudo para reduzir fragilidade associada a fontes de sinal sem destruir retorno. A hipótese não remove uma fonte do sistema principal, não altera o score e não muda o ranking principal.

## Variações

A calibração testa variações paramétricas com:

- limitação de `quant`, `technical` ou `integrated`;
- confirmação por duas fontes;
- confirmação integrada;
- controle de custo;
- controle de slippage;
- filtro por regime;
- filtro por ativo frágil;
- filtro por turnover.

## Governança

Uma variação só pode seguir para observação recorrente se passar por retorno, drawdown, fragilidade, custo, slippage, amostra e overfitting. Variações bloqueadas por governança exigem nova investigação necessária.

## Não recomendação

Este módulo é simulação, investigação e validação. Não executa ordens reais, não recomenda compra/venda e não aplica variações automaticamente.

