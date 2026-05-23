# Paper Trading - Simulação de Redução de Custos

## Objetivo

Testar variantes simuladas para reduzir custo de saída e rebalanceamento usando os buckets finos de custo como alvo.

## Comando

```powershell
python -m src.scanners.cost_reduction_simulation --paper-run-id 2 --save-db --csv
```

## Leitura

Cada variante simulada compara:

- redução de custo total;
- redução de custo de saída;
- redução de custo de rebalanceamento;
- delta de retorno;
- delta de drawdown;
- delta de turnover;
- governança.

## Governança

Uma variante só segue para mais testes quando reduz custo sem destruir retorno, sem aumentar drawdown e sem cortar amostra demais.

## Não recomendação

Esta rotina não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica variante automaticamente.

## Fronteira custo-retorno-drawdown

Depois de salvar uma simulação de redução de custos, rode:

```powershell
python -m src.scanners.cost_frontier_analysis --cost-reduction-run-id 3 --save-db --csv
```

A análise identifica fronteira eficiente, variantes dominadas e governança de trade-off.
