# Walk-forward E Fora Da Amostra

## Objetivo

A análise fora da amostra mede se o `score_final` continua funcionando em períodos que não foram usados para observar ou calibrar o modelo.

O walk-forward repete esse processo em várias janelas: observa um período de treino, testa no período seguinte e avança a janela no tempo. Isso reduz o risco de confiar em um score que apenas se ajustou bem ao passado.

## Comando Operacional

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db
```

Com retorno líquido:

```powershell
python -m src.scanners.walk_forward_quant_analysis --start 2024-01-01 --end 2026-12-31 --train-months 12 --test-months 3 --csv --save-db --net
```

Walk-forward dos filtros de qualidade:

```powershell
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
```

Antes dele, gere o backtest histórico:

```powershell
python -m src.scanners.historical_quant_backtest --start 2024-01-01 --end 2026-12-31 --csv --save-db
```

## Metodologia

Para cada janela:

1. separa o período de treino;
2. separa o período de teste imediatamente posterior;
3. identifica o melhor `signal_type` no treino;
4. mede esse mesmo sinal no teste;
5. identifica o melhor `score_bucket` no treino;
6. mede esse mesmo bucket no teste;
7. calcula degradação de performance;
8. marca alerta quando o que funcionou no treino falha no teste.

## Como Interpretar

Janelas positivas indicam a proporção de períodos de teste com retorno médio positivo.

Degradação de performance compara o retorno do melhor sinal no treino com o retorno desse mesmo sinal no teste.

Alerta de overfitting aparece quando o sinal ou bucket que funcionou no treino tem retorno negativo no teste, ou quando poucas janelas ficam positivas.

Estabilidade de sinais e buckets mostra se o mesmo tipo de sinal ou faixa de score aparece repetidamente como melhor alternativa de treino.

## Persistência

As tabelas salvas são:

- `walk_forward_runs`;
- `walk_forward_results`.
- `filter_walk_forward_runs`;
- `filter_walk_forward_results`.

O backtest histórico também persiste os componentes completos do score em `historical_backtest_results`, permitindo análise direta na Mesa Quant.

## Limitações

- O walk-forward usa resultados diários, não execução intraday.
- Custos, slippage e spread entram apenas quando há retorno líquido salvo.
- Poucas janelas reduzem a confiabilidade.
- Resultado positivo fora da amostra não garante repetição futura.
- Nenhum peso é alterado automaticamente.
- A análise não é recomendação financeira.
- O modo líquido usa estimativas de custo e slippage, não execução real no book.
