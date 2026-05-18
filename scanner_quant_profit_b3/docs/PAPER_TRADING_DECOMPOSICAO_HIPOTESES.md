# Paper Trading - Decomposição de Hipóteses

## Decomposição por ativo

A rotina calcula, por ticker:

- quantidade de trades simulados;
- delta médio de retorno;
- delta médio de drawdown;
- delta médio de fragilidade;
- percentual de melhora positiva;
- sensibilidade a custo;
- sensibilidade a slippage;
- contribuição para bloqueio.

Classificações:

- `ASSET_HELPS_HYPOTHESIS`
- `ASSET_HURTS_HYPOTHESIS`
- `ASSET_NEUTRAL`
- `ASSET_INSUFFICIENT_DATA`

## Decomposição por fonte de sinal

A rotina calcula, por `quant`, `technical` e `integrated`:

- delta médio de retorno;
- delta médio de drawdown;
- delta médio de fragilidade;
- percentual de melhora positiva;
- janelas úteis;
- motivo dominante de bloqueio.

Classificações:

- `SOURCE_SUPPORTS_HYPOTHESIS`
- `SOURCE_WEAKENS_HYPOTHESIS`
- `SOURCE_INSUFFICIENT_DATA`
- `SOURCE_MIXED`

## Uso

```powershell
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
```

As decomposições não recomendam compra/venda e não aplicam hipótese automaticamente.

