# Mudanças de Status Integrado

A mudança de status integrado é um evento de auditoria. Ela mostra que a leitura consolidada por ativo mudou entre snapshots.

## Tipos de Mudança

- `STATUS_CHANGE`
- `GOVERNANCE_CHANGE`
- `SCORE_CHANGE`
- `VALUATION_CHANGE`
- `TECHNICAL_CHANGE`
- `QUANT_CHANGE`
- `EVENT_CHANGE`
- `REGIME_CHANGE`
- `OPTIONS_CHANGE`
- `DATA_QUALITY_CHANGE`
- `NO_MATERIAL_CHANGE`

## Critérios Materiais

São mudanças materiais:

- mudança em `integrated_status`;
- mudança em `integrated_governance_status`;
- variação relevante de `integrated_score`;
- piora forte de qualidade de dados;
- mudança de valuation, evento, regime ou opções.

## Linguagem

As explicações usam linguagem analítica:

- "mudou para bloqueado por governança";
- "qualidade de dados piorou";
- "contexto de evento mudou";
- "regime principal mudou".

Não usar como chamada operacional.
