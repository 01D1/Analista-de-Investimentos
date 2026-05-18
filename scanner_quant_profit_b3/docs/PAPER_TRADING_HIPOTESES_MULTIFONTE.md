# Paper Trading - Hipóteses Multifonte

## Fontes

O ranking usa fontes de sinal em estudo:

- `quant`;
- `technical`;
- `integrated`.

Cada hipótese é testada contra o baseline da própria fonte. Isso evita comparar uma hipótese aplicada em `technical` contra um baseline dominado por `quant`.

## Universo Padrão

As hipóteses incluem redução de exposição, exclusão simulada de ativos frágeis, limitação de fonte, confirmação integrada/técnica, bloqueio de contribuidores de drawdown, exclusão de risco de evento e filtro de regime de liquidez fraca.

## Governança

Status possíveis:

- `HYPOTHESIS_RANK_APPROVED_FOR_OBSERVATION`
- `HYPOTHESIS_RANK_MORE_TESTING_REQUIRED`
- `HYPOTHESIS_RANK_BLOCKED_OVERFITTING`
- `HYPOTHESIS_RANK_BLOCKED_COST_SENSITIVE`
- `HYPOTHESIS_RANK_BLOCKED_LOW_COVERAGE`
- `HYPOTHESIS_RANK_REJECTED`

Para aprovação de observação, a hipótese precisa ter score de robustez alto, ao menos duas fontes úteis, retorno não deteriorado, drawdown sem piora, fragilidade reduzida e ausência de flags fortes de custo ou overfitting.

## Relatório

Depois de salvar um ranking:

```powershell
python -m src.scanners.generate_hypothesis_ranking_report --run-id 1
```

O relatório é investigação e validação. Não recomenda compra/venda e não aplica hipótese automaticamente.

## Deep Dive Multifonte

Para explicar por que as melhores hipóteses foram bloqueadas:

```powershell
python -m src.scanners.hypothesis_deep_dive --ranking-run-id 1 --top-n 3 --save-db --csv
```

A rotina decompõe a hipótese em estudo por `quant`, `technical`, `integrated`, regime, custo, slippage e ativo. Se a evidência for mista ou insuficiente, o bloqueio é registrado como nova investigação necessária.
