# Cobertura das Fontes de Sinal

## Objetivo

Este processo mede se as fontes de sinal em estudo têm população histórica suficiente para paper trading, validação OOS e comparação multi-fonte.

Ele não executa ordens reais, não recomenda compra ou venda, não altera o score principal, não altera ranking e não aplica hipóteses automaticamente.

## Fontes Avaliadas

- `quant`: sinais persistidos pelo backtest quantitativo histórico.
- `technical`: setups técnicos persistidos pela população histórica técnica.
- `integrated`: snapshots de inteligência integrada persistidos por data e ativo.
- `options`: estruturas de opções, quando houver histórico persistido.

## Comando

```powershell
python -m src.scanners.signal_coverage_check --start 2026-01-02 --end 2026-04-30 --sources quant technical integrated --save-db --csv
```

## Métricas

- quantidade de sinais;
- quantidade de tickers;
- primeira e última data persistida;
- dias úteis ativos;
- regimes cobertos, quando existirem;
- células úteis de amostra;
- percentual de cobertura;
- status de cobertura e requisitos.

## Status

- `COBERTURA_BOA`
- `COBERTURA_MEDIA`
- `COBERTURA_FRACA`
- `COBERTURA_INSUFICIENTE`
- `SEM_DADOS`

Para OOS com cobertura obrigatória, uma fonte relevante deve ter pelo menos 30 sinais, 2 tickers, 10 dias úteis, 2 regimes quando regimes existirem, e 50% de cobertura útil.

Se a amostra não cumprir esses limites, a conclusão de robustez deve ser bloqueada como `COVERAGE_INSUFFICIENT`.

