# Estruturas de Opções

## Objetivo

As estruturas de opções ajudam a transformar opções individuais em payoffs comparáveis. A camada atual monta estruturas básicas para estudo quantitativo e aplica ranking e governança.

Ela não executa ordens e não recomenda operação. A linguagem esperada é analítica: assimetria a investigar, estrutura potencial a estudar, risco elevado, liquidez insuficiente ou dados insuficientes.

## Estruturas Iniciais

O scanner prepara:

- `LONG_CALL`;
- `LONG_PUT`;
- `BULL_CALL_SPREAD`;
- `BEAR_PUT_SPREAD`;
- `CALL_DEBIT_SPREAD`;
- `PUT_DEBIT_SPREAD`.

Estruturas como `COVERED_CALL`, `PROTECTIVE_PUT` e `CASH_SECURED_PUT` exigem contexto de posição em ação ou caixa e devem ser tratadas como expansão futura antes de qualquer uso operacional.

## Métricas Da Estrutura

Cada estrutura possui:

- pernas em JSON;
- débito líquido;
- crédito líquido;
- lucro máximo teórico, quando calculável;
- perda máxima teórica;
- pontos de breakeven;
- relação payoff/risco;
- score de liquidez;
- score de risco;
- score final da estrutura;
- explicação textual;
- status de governança.

## Ranking

O score da estrutura usa componentes como:

- payoff;
- liquidez;
- risco;
- custo;
- decaimento temporal;
- moneyness;
- volatilidade;
- regime e evento, quando houver contexto disponível.

O score penaliza spread alto, baixa liquidez, vencimento curto, risco difícil de limitar e dados insuficientes.

## Interpretação

Uma estrutura com score alto ainda precisa de análise operacional. Uma estrutura bloqueada por liquidez ou dados deve ser descartada do estudo estatístico até haver dados melhores.

O ranking serve para priorizar investigação, não para acionar execução.

## Backtest Preliminar

Depois de construir histórico da cadeia, é possível simular estruturas com custos por perna:

```powershell
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
```

O backtest usa bid/ask quando disponível e marca entradas como puladas quando faltam dados ou liquidez.
