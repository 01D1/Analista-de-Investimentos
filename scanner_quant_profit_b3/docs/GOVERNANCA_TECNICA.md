# Governança Técnica

A governança técnica classifica setups sem alterar score, ranking ou filtros principais.

Status:

- `TECH_APPROVED_FOR_STUDY`
- `TECH_OBSERVATION_ONLY`
- `TECH_BLOCKED_INSUFFICIENT_DATA`
- `TECH_BLOCKED_OVERFITTING`
- `TECH_BLOCKED_LOW_LIQUIDITY`
- `TECH_BLOCKED_HIGH_VOLATILITY`
- `TECH_BLOCKED_NEGATIVE_NET_RETURN`

Critérios iniciais:

- amostra mínima;
- retorno médio positivo em D+5;
- hit rate mínimo;
- baixa concentração;
- custos aceitáveis quando disponíveis;
- validação fora da amostra em fases futuras.

`TECH_APPROVED_FOR_STUDY` significa apenas que a estrutura merece estudo adicional. Não é recomendação operacional.

## Governança OOS

A Fase 23 adiciona a classificação fora da amostra após walk-forward técnico:

- `TECH_OOS_APPROVED_FOR_STUDY`
- `TECH_OOS_OBSERVATION_ONLY`
- `TECH_OOS_BLOCKED_OVERFITTING`
- `TECH_OOS_BLOCKED_INSUFFICIENT_DATA`
- `TECH_OOS_BLOCKED_NEGATIVE_RETURN`

Essa camada impede que um setup seja considerado robusto apenas por ter performado bem dentro da amostra.
