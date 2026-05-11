# Custos E Execucao

## Objetivo

O modo líquido aproxima o backtest de uma execução operacional mais realista. Ele aplica custos, slippage e penalizações de liquidez aos retornos futuros do backtest histórico.

Ele não altera o score, não muda o ranking principal e não gera recomendação financeira.

## Retorno Bruto X Retorno Líquido

Retorno bruto é o retorno estatístico calculado entre o preço teórico de entrada e o preço futuro.

Retorno líquido desconta:

- custos estimados;
- slippage de entrada;
- slippage de saída;
- penalização por baixa liquidez.

Um sinal pode parecer bom no bruto e deixar de ser interessante no líquido quando custos e execução pesam demais.

## Bps

Bps significa basis points. Cada 1 bp equivale a 0,01%.

Exemplo:

- 10 bps = 0,10%;
- 5 bps = 0,05%.

No round trip, o custo é aplicado na entrada e na saída.

## Slippage

Slippage é a diferença entre o preço teórico e o preço executado.

No modelo atual:

- compra executa acima do preço teórico;
- venda executa abaixo do preço teórico.

Isso torna o retorno líquido menor que o retorno bruto.

## Spread E Liquidez

Liquidez importa porque um sinal estatístico pode não ser executável em tamanho real.

O sistema classifica a qualidade de execução como:

- `EXCELENTE`;
- `BOA`;
- `ACEITAVEL`;
- `RUIM`;
- `INVIAVEL`.

Sinais `RUIM` e `INVIAVEL` podem ser removidos com `--only-tradeable`.

## Comando Backtest Líquido

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db --net --cost-bps 10 --slippage-bps 5 --min-volume 5000000
```

Para remover sinais ruins ou inviáveis:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db --net --cost-bps 10 --slippage-bps 5 --min-volume 5000000 --only-tradeable
```

## Filtros Após Custos

Se o retorno líquido ficar negativo depois de custos e slippage, use filtros opcionais para medir se sinais mais seletivos preservam alguma vantagem estatística:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --min-execution-quality BOA --csv
```

Para testar thresholds sem aplicá-los automaticamente:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv
```

Esses filtros são diagnósticos. Uma melhora no passado pode ser overfitting se a amostra ficar pequena ou concentrada em poucos ativos.

## Walk-forward Líquido

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db --net
```

Se as colunas líquidas já existirem no banco, o walk-forward usa essas colunas. Caso contrário, ele calcula uma camada líquida temporária com os parâmetros informados.

## Limitações

- Custos e slippage são aproximações.
- O modelo não conhece o book real no momento da execução.
- Spread histórico pode não estar disponível para ações.
- Volume financeiro diário não garante execução intraday.
- O modo líquido melhora o realismo, mas não substitui validação operacional.
