# Walk-forward Dos Filtros

## Objetivo

O walk-forward dos filtros valida thresholds fora da amostra. A ideia é evitar que um filtro pareça bom apenas porque foi ajustado ao período usado na otimização exploratória.

Essa camada não altera o score padrão, não muda o ranking principal, não aplica thresholds automaticamente e não gera recomendação financeira.

## Diferença Entre Otimização E Robustez

A otimização exploratória encontra combinações de filtros que funcionaram em uma amostra.

O walk-forward testa se esses filtros continuam funcionando em janelas futuras:

1. escolhe thresholds no treino;
2. aplica os thresholds no teste seguinte;
3. mede retorno líquido, hit rate, amostra e concentração;
4. repete o processo em várias janelas.

Um filtro só começa a ser considerado robusto quando sobrevive fora da amostra.

## Métricas

O relatório mede:

- percentual de janelas positivas;
- retorno líquido médio no teste;
- hit rate médio no teste;
- sinais médios por janela;
- concentração no ativo mais frequente;
- concentração nos 3 ativos mais frequentes;
- alertas de amostra insuficiente;
- alertas de concentração excessiva;
- alerta de overfitting.

## Robustez

As classificações são:

- `ROBUSTO`: maioria das janelas positivas, retorno líquido positivo, hit rate acima de 50% e concentração aceitável;
- `PROMISSOR`: resultado positivo, mas ainda com ressalvas;
- `FRAGIL`: evidência fraca ou instável;
- `OVERFIT_PROVAVEL`: treino bom e teste ruim, concentração excessiva ou degradação forte;
- `AMOSTRA_INSUFICIENTE`: poucas janelas ou poucos sinais por janela.

Essas classes são diagnósticas. Nenhuma delas aplica thresholds automaticamente.

## Comando

Antes, salve um backtest líquido no banco:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --csv --save-db
```

Depois rode:

```powershell
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
```

Depois gere o review de governança:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
```

O CSV gerado segue o padrão:

```text
data/reports/filter_walk_forward_results_YYYYMMDD_HHMMSS.csv
```

## Persistência

As tabelas são:

- `filter_walk_forward_runs`;
- `filter_walk_forward_results`.
- `governance_reviews`, quando o review de governança for salvo.

## Como Interpretar

Janelas positivas indicam quantas janelas de teste tiveram retorno líquido médio acima de zero.

Concentração top 3 mostra se o resultado depende de poucos ativos. Uma concentração elevada reduz a confiança estatística.

Overfitting provável aparece quando o treino é bom, mas o teste seguinte perde retorno, fica negativo ou concentra demais.

Se o review de governança classificar o candidato como `BLOQUEADO_OVERFITTING`, `AMOSTRA_INSUFICIENTE`, `CONCENTRACAO_EXCESSIVA` ou `LIQUIDEZ_INSUFICIENTE`, o candidato deve permanecer fora de qualquer uso operacional.

## Regimes De Mercado

Antes de considerar filtros robustos, avalie também por regime:

```powershell
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --with-regimes --csv --save-db
```

Um filtro pode ser promissor em `ALTA_TENDENCIAL` e frágil em `ALTA_VOLATILIDADE`. A governança por regime impede aprovação ampla quando o desempenho está concentrado em um único ambiente.

## Limitações

- Depende de backtest líquido salvo previamente.
- Usa retornos diários, não execução intraday.
- O grid de thresholds é conservador, mas ainda pode overfitar.
- A validação por janela reduz risco de superajuste, mas não elimina risco operacional.
