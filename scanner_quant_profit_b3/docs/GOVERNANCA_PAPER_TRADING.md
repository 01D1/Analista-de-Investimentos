# Governança de Paper Trading

Status:

- `PAPER_APPROVED_FOR_REVIEW`
- `PAPER_OBSERVATION_ONLY`
- `PAPER_BLOCKED_DRAWDOWN`
- `PAPER_BLOCKED_NEGATIVE_RETURN`
- `PAPER_BLOCKED_LOW_SAMPLE`
- `PAPER_BLOCKED_HIGH_TURNOVER`
- `PAPER_BLOCKED_RISK_LIMITS`
- `PAPER_ADVANCED_RULES_IMPROVED`
- `PAPER_ADVANCED_RULES_NO_IMPROVEMENT`
- `PAPER_BLOCKED_OVERTRADING`
- `PAPER_BLOCKED_RULE_OVERFIT`
- `PAPER_REQUIRES_MORE_DATA`

Critérios:

- amostra mínima de ordens simuladas;
- retorno simulado;
- drawdown;
- turnover;
- exposição e risco.
- excesso de saídas simuladas;
- rebalanceamento excessivo;
- evidência insuficiente para regras avançadas.

A governança é observacional. Mesmo um status aprovado significa apenas “aprovado para revisão”, não autorização operacional.

## Governanca OOS das regras

Status adicionais:

- `PAPER_OOS_APPROVED_FOR_STUDY`
- `PAPER_OOS_OBSERVATION_ONLY`
- `PAPER_OOS_BLOCKED_OVERFITTING`
- `PAPER_OOS_BLOCKED_DRAWDOWN`
- `PAPER_OOS_BLOCKED_LOW_SAMPLE`
- `PAPER_OOS_BLOCKED_TURNOVER`
- `PAPER_OOS_BLOCKED_NEGATIVE_RETURN`
- `PAPER_OOS_BLOCKED_DATA`

Critérios:

- janelas positivas;
- retorno medio fora da amostra;
- drawdown medio;
- trades suficientes;
- turnover aceitavel;
- ausencia de overfitting evidente.

Aprovado para estudo nao significa autorizacao operacional.
