# Calibração de Setups Técnicos

A calibração testa thresholds de score técnico, score do setup, confiança, volume, tendência e momentum.

Ela responde: “quais filtros reduzem ruído sem destruir a amostra?”

## Métricas

- quantidade de sinais;
- retorno médio por horizonte;
- hit rate D+5;
- payoff;
- concentração no principal ativo;
- alerta de amostra pequena;
- alerta de risco de overfitting.

## Cuidado

Thresholds encontrados por grid search são exploratórios. Eles não são aplicados automaticamente no scanner técnico nem no scanner principal.

