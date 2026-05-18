# Fragilidade da Carteira Simulada

Esta camada de diagnostico explica por que uma carteira simulada perde robustez. Ela decompoe P&L, custos, slippage, drawdown, ativos e fontes de sinal.

Comando:

```powershell
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
```

A rotina mede:

- fragility score geral;
- contribuicao por ativo;
- contribuicao por fonte de sinal;
- custo e slippage por ativo;
- periodos de drawdown;
- governanca de fragilidade.

Status:

- `PAPER_FRAGILITY_OK`
- `PAPER_FRAGILITY_OBSERVATION`
- `PAPER_FRAGILITY_BLOCKED_COST`
- `PAPER_FRAGILITY_BLOCKED_DRAWDOWN`
- `PAPER_FRAGILITY_BLOCKED_CONCENTRATION`
- `PAPER_FRAGILITY_BLOCKED_SIGNAL_SOURCE`
- `PAPER_FRAGILITY_BLOCKED_DATA`

O diagnostico nao executa ordens reais, nao recomenda compra ou venda e nao altera score/ranking.

## Investigacoes Derivadas

Depois de salvar um diagnostico, rode:

```powershell
python -m src.scanners.paper_investigation --paper-run-id 2 --fragility-run-id 1 --save-db --csv
```

Essa rotina gera hipoteses de investigacao, como exclusao simulada de ativo critico, limite analitico de custo por ativo, reducao de fonte fragil ou simulacao sem rebalanceamento. Os resultados sao apenas comparacao antes/depois em paper trading.
