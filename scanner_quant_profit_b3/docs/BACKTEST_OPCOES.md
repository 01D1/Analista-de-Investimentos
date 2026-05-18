# Backtest de Opções

## Objetivo

Este documento descreve o estado do backtest de opções. A camada atual implementa um backtest preliminar de estruturas usando snapshots históricos, bid/ask, custos por perna e vencimento econômico simples. Ela ainda não é um backtest operacional completo.

## Por Que É Mais Difícil

Backtest de opções exige histórico de cadeia por data, não apenas preço do ativo-objeto. Para ser minimamente realista, precisa preservar:

- bid e ask históricos;
- vencimentos disponíveis em cada data;
- strikes negociados;
- volume, negócios e interesse aberto;
- custos, slippage e spread;
- exercício e vencimento;
- rolagem;
- eventos corporativos;
- liquidez por estrutura.

Sem esses elementos, o backtest pode superestimar retornos e subestimar risco.

## Comandos Atuais

```powershell
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
```

## Requisitos Para Evoluir

Uma implementação robusta deve:

- salvar snapshots históricos de cadeias de opções;
- reconstruir a cadeia disponível na data do sinal;
- calcular entrada e saída usando bid/ask, não apenas último preço;
- tratar vencimento, exercício e opções sem negócio;
- aplicar custos e slippage por perna;
- medir capacidade por liquidez;
- comparar estruturas por regime e evento;
- submeter candidatos à governança antes de qualquer promoção.

## Limitações Atuais

O backtest atual calcula valor econômico de vencimento e execução estimada por perna, mas ainda não simula exercício real complexo, rolagem, profundidade de livro, chamadas de margem ou impacto de mercado.

Qualquer conclusão operacional precisa esperar histórico amplo de cadeia, walk-forward de estruturas e governança específica por regime, evento e liquidez.
