# Alertas da Inteligência Integrada

A Fase 25 cria alertas derivados de mudanças materiais nos snapshots integrados.

## Alertas

- `ASSET_STATUS_CHANGED`
- `ASSET_GOVERNANCE_BLOCKED`
- `ASSET_GOVERNANCE_UNBLOCKED`
- `ASSET_SCORE_DROPPED`
- `ASSET_SCORE_IMPROVED`
- `ASSET_VALUATION_CHANGED`
- `ASSET_EVENT_RISK_CHANGED`
- `ASSET_REGIME_CHANGED`
- `ASSET_DATA_QUALITY_DROPPED`

## Severidade

- `CRITICAL`: status passa para bloqueado ou mudança crítica.
- `WARNING`: governança muda, score cai muito, qualidade de dados piora.
- `INFO`: melhora de score ou mudança informativa.

## Persistência

Quando o comando de diff roda com `--save-db`, os alertas podem ser salvos em `operational_alerts`.

```bash
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
```

Esses alertas não disparam operação. Eles apenas chamam atenção para auditoria.
