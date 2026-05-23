# Paper Trading - Break-even de Custo

## Objetivo

A análise de break-even estima quanto custo e slippage a estratégia simulada suporta antes de o retorno ficar negativo. Também estima a redução de turnover necessária para preservar edge.

## Métricas

- custo máximo suportado em bps;
- slippage máximo suportado em bps;
- cenário em que o retorno fica negativo;
- redução de turnover para break-even;
- retorno por trade necessário.

## Comando

```powershell
python -m src.scanners.cost_slippage_diagnostics --paper-run-id 2 --save-db --csv
```

Tudo permanece como simulação e validação analítica.

