# Estabilidade de Opções

## Objetivo

A estabilidade de opções avalia se o resultado depende de um único vencimento, moneyness, estrutura, liquidez, regime ou evento.

Essa análise evita tratar como robusta uma estrutura que só funcionou em uma fatia estreita da amostra.

## Dimensões

O sistema resume resultados por:

- bucket de DTE: `0_7`, `8_15`, `16_30`, `31_60`, `61_90`, `90_PLUS`;
- moneyness: `DEEP_ITM`, `ITM`, `ATM`, `OTM`, `DEEP_OTM`, `UNKNOWN`;
- tipo de estrutura;
- qualidade de execução;
- regime de mercado, quando disponível;
- contexto de evento, quando disponível.

## Alertas

Alertas comuns:

- performance concentrada em vencimento específico;
- performance só em moneyness específico;
- baixa liquidez;
- alto custo médio;
- amostra insuficiente.

Esses alertas não alteram modelo ou ranking. Eles apenas orientam análise e governança.

