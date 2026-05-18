# Histórico da Inteligência Integrada por Ativo

A Fase 25 adiciona histórico comparativo dos snapshots integrados por ativo. O objetivo é rastrear como a leitura analítica mudou ao longo do tempo, sem alterar score principal, ranking ou filtros.

## O Que É Comparado

Para cada ticker, o sistema compara o penúltimo e o último registro de `asset_intelligence_snapshots`.

Campos monitorados:

- score e status integrado;
- governança integrada;
- qualidade dos dados;
- camada técnica;
- camada quant;
- valuation/fundamentos;
- eventos;
- regimes;
- opções.

## Tabela

Os resultados são salvos em:

- `asset_intelligence_diffs`

Essa tabela mantém:

- snapshots anterior e atual;
- campos alterados;
- delta de score;
- delta de qualidade de dados;
- flags por camada;
- tipo de mudança material;
- explicação textual.

## Comando

```bash
python -m src.scanners.asset_intelligence_diff --latest --save-db --csv
```

## Relatório por Ativo

```bash
python -m src.scanners.generate_asset_change_reports --tickers PETR4 VALE3 --output-dir data/reports/asset_intelligence_changes
```

## Interpretação

Mudança material não é recomendação. Ela indica que algo mudou na leitura integrada e merece auditoria.

Exemplos:

- status integrado mudou;
- governança passou a bloquear;
- score caiu ou subiu muito;
- valuation mudou;
- evento ou regime mudou;
- qualidade dos dados piorou.
