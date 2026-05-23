# Paper Trading - Custos de Regras de Saída

## Objetivo

Separar custo atribuído a eventos de saída:

- stop loss;
- take-profit;
- trailing stop;
- perda diária/semanal;
- tempo;
- fechamento de simulação;
- metadado ausente.

## Classes

- `EXIT_RULE_EFFICIENT`
- `EXIT_RULE_COSTLY`
- `EXIT_RULE_DESTROYS_EDGE`
- `EXIT_RULE_INSUFFICIENT_DATA`

## Não recomendação

O relatório explica origem de custo e fragilidade, mas não recomenda compra/venda nem altera parâmetros operacionais.
