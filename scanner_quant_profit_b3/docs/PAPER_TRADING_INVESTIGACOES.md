# Paper Trading - Investigacoes Analiticas

Esta camada gera hipoteses de investigacao para reduzir fragilidade da carteira simulada. Ela nao executa ordens reais, nao recomenda compra/venda, nao altera score principal e nao altera ranking.

## Objetivo

Transformar diagnosticos de fragilidade em experimentos simulados:

- exclusao simulada de ativos criticos;
- limite analitico de custo por ativo;
- reducao ou exclusao simulada de fonte de sinal fragil;
- simulacao sem rebalanceamento;
- reducao simulada de exposicao quando drawdown e fragil;
- comparacao antes/depois contra o paper run base.

## Comando

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
```

Dry-run:

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --dry-run --csv
```

## Saidas

- `paper_investigation_runs`
- `paper_investigation_results`
- CSV `paper_investigation_results_YYYYMMDD_HHMMSS.csv`
- relatorio Markdown via `generate_paper_investigation_report`

## Governanca

Status possiveis:

- `INVESTIGATION_APPROVED_FOR_FURTHER_TEST`
- `INVESTIGATION_OBSERVATION_ONLY`
- `INVESTIGATION_REJECTED`
- `INVESTIGATION_BLOCKED_OVERFITTING`
- `INVESTIGATION_BLOCKED_LOW_SAMPLE`
- `INVESTIGATION_BLOCKED_TRADEOFF`

Uma hipotese aprovada aqui significa apenas aprovada para novo teste, preferencialmente multi-cenario e fora da amostra.

## Validacao OOS

Hipoteses promissoras devem ser validadas com:

```powershell
python -m src.scanners.hypothesis_oos_validation --investigation-run-id 1 --hypothesis-id REDUCE_VOLATILITY_EXPOSURE --save-db --csv
```

Somente a governanca OOS pode indicar se a hipotese fica em observacao recorrente.

## Ranking Multi-Fonte

Com `quant`, `technical` e `integrated` populados, rode o ranking de hipóteses:

```powershell
python -m src.scanners.hypothesis_ranking --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
```

O ranking compara hipóteses em múltiplas fontes e classifica apenas para observação simulada. Ele não recomenda compra/venda e não aplica ajustes automaticamente.
