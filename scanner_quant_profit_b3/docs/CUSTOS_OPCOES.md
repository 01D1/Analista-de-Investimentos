# Custos de Execução em Opções

## Objetivo

A camada de custos de opções estima execução por perna usando bid/ask, fallback para último preço, custo em bps e slippage em bps.

Ela serve para aproximar o backtest de uma execução mais realista, sem executar ordens.

## Preço de Execução

Regras:

- compra usa `ask`;
- venda usa `bid`;
- se bid/ask estiver ausente, usa último preço ajustado por slippage;
- se não houver preço suficiente, a perna é marcada como dados insuficientes.

## Custos Calculados

O modelo estima:

- custo transacional por perna;
- custo de slippage;
- custo de spread;
- valor financeiro estimado da execução;
- qualidade de execução.

## Qualidade de Execução

Classificações:

- `EXCELENTE`;
- `BOA`;
- `ACEITAVEL`;
- `RUIM`;
- `INVIAVEL`;
- `DADOS_INSUFICIENTES`.

Baixo volume, poucos negócios ou spread alto reduzem a qualidade e podem bloquear o backtest ou a governança.

## Limitações

O modelo ainda não substitui leitura real de livro, profundidade, fila, impacto de mercado, exercício operacional ou roteamento. A função é estatística e conservadora.

