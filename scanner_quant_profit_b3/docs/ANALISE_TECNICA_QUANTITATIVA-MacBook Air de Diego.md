# Análise Técnica Quantitativa

A Fase 22 adiciona uma camada opcional para transformar leitura técnica em features matemáticas, setups auditáveis, score técnico paralelo, backtest exploratório e governança.

Ela não altera o score principal, não substitui ranking e não gera recomendação financeira.

## Fluxo

1. Carrega preços diários do SQLite.
2. Calcula indicadores de tendência, momentum, volatilidade, volume, suporte/resistência e padrões objetivos.
3. Detecta setups parametrizados.
4. Calcula `technical_score_final`.
5. Classifica por governança técnica.
6. Opcionalmente roda backtest por horizontes futuros.

## Comando

```bash
python -m src.scanners.technical_analysis_scanner --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --save-db --csv --with-backtest
```

## Saídas

- `technical_feature_snapshots`
- `technical_setup_signals`
- `technical_backtest_runs`
- `technical_backtest_results`
- `technical_walk_forward_runs`
- `technical_walk_forward_results`
- `technical_threshold_optimization_runs`
- `technical_setup_dedup_runs`
- CSVs em `data/reports`

## Validação Fora da Amostra

Após o backtest exploratório, rode o walk-forward técnico:

```bash
python -m src.scanners.technical_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --tickers PETR4 VALE3 ITUB4 --train-months 3 --test-months 1 --dedupe --optimize-thresholds --save-db --csv
```

Esse comando reduz redundância, testa thresholds e classifica a robustez OOS.

## Linguagem

Use os resultados como “setup técnico detectado”, “padrão a investigar” ou “sinal técnico em observação”. Não use como call operacional.
