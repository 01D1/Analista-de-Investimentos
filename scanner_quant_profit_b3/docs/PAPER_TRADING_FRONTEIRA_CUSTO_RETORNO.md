# Paper Trading - Fronteira Custo-Retorno-Drawdown

## Objetivo

Identificar variantes em estudo que ficam na fronteira eficiente entre redução de custo, preservação de retorno, controle de drawdown e turnover.

## Comando

```powershell
python -m src.scanners.cost_frontier_analysis --cost-reduction-run-id 3 --save-db --csv
```

## Como ler

Uma variante é dominada quando outra variante:

- reduz mais custo;
- preserva melhor retorno;
- controla melhor drawdown;
- tem menor turnover.

Variantes na fronteira eficiente não são aprovadas automaticamente. Elas apenas merecem análise adicional se passarem governança.

## Não recomendação

A fronteira é uma análise de simulação. Não executa ordens reais, não recomenda compra/venda, não altera score/ranking e não aplica variante automaticamente.
