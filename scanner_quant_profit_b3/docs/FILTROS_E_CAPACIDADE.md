# Filtros E Capacidade

## Objetivo

A camada de filtros e capacidade torna o backtest líquido mais seletivo sem alterar o score padrão, o ranking principal ou os pesos do modelo.

Ela existe porque um `score_final` alto não significa, sozinho, que o sinal é operacional. Um sinal também precisa sobreviver a custos, slippage, qualidade de execução, liquidez mínima, risco e tamanho viável.

## Filtros De Qualidade

O módulo `src.quant.signal_filters` classifica sinais como:

- `ALTA_QUALIDADE`;
- `BOA_QUALIDADE`;
- `QUALIDADE_MEDIA`;
- `BAIXA_QUALIDADE`;
- `DESCARTAR`.

Os filtros opcionais podem considerar:

- `score_final` mínimo;
- confiança mínima do sinal;
- qualidade mínima de execução;
- volume e negócios mínimos;
- `score_liquidez` mínimo;
- `score_risco` mínimo;
- remoção de sinais `RUIM` ou `INVIAVEL`;
- tipos de sinal permitidos;
- retorno líquido esperado positivo, quando houver histórico semelhante.

## Thresholds

O módulo `src.quant.threshold_optimizer` testa combinações de thresholds e mede:

- quantidade de sinais restantes;
- retorno líquido médio em D+1, D+3, D+5 e D+10;
- hit rate líquido;
- payoff;
- drawdown médio;
- percentual removido;
- concentração em poucos ativos.

O otimizador apenas sugere combinações. Ele não aplica thresholds automaticamente ao scanner nem muda o ranking principal.

## Capacidade Por Liquidez

O módulo `src.quant.capacity` estima capacidade operacional usando participação máxima no volume financeiro.

Exemplo:

- volume diário de R$ 10.000.000;
- participação máxima de 1%;
- capacidade estimada de R$ 100.000.

Também há sizing por risco:

- capital disponível;
- risco percentual;
- preço de entrada;
- stop técnico.

O tamanho final é limitado por risco, capital e liquidez. A classificação de capacidade pode ser:

- `ALTA_CAPACIDADE`;
- `BOA_CAPACIDADE`;
- `CAPACIDADE_LIMITADA`;
- `BAIXA_CAPACIDADE`;
- `INVIAVEL`.

## Comandos

Backtest líquido com filtro de qualidade:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv
```

Com qualidade mínima de execução:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --min-execution-quality BOA --csv
```

Otimização exploratória de thresholds:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --optimize-thresholds --csv
```

Validação walk-forward dos filtros:

```powershell
python -m src.scanners.filter_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --train-months 1 --test-months 1 --csv --save-db
```

Review de governança:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
```

Para persistir no SQLite:

```powershell
python -m src.scanners.historical_quant_backtest --start 2026-01-02 --end 2026-04-30 --net --quality-filter --min-score-final 80 --csv --save-db
```

## CSVs Gerados

Quando `--quality-filter` é usado:

- `data/reports/filter_impact_YYYYMMDD_HHMMSS.csv`.

Quando `--optimize-thresholds` é usado:

- `data/reports/threshold_optimization_YYYYMMDD_HHMMSS.csv`.

## Tabelas

As tabelas opcionais são:

- `quality_filter_runs`;
- `threshold_optimization_runs`.
- `filter_walk_forward_runs`;
- `filter_walk_forward_results`.
- `governance_reviews`.

O backtest histórico também pode persistir:

- `signal_quality`;
- `estimated_capacity`;
- `capacity_class`;
- `volume`;
- `trades`.

## Risco De Overfitting

Filtros muito específicos podem melhorar o passado e falhar no futuro. Por isso:

- não use uma combinação só porque foi a melhor no grid;
- exija amostra mínima;
- valide fora da amostra;
- compare com walk-forward;
- rode o walk-forward dos filtros antes de considerar qualquer threshold robusto;
- monitore concentração em poucos ativos.

## Limitações

- Capacidade por volume diário é aproximação.
- O modelo não conhece book real, fila, spread intraday ou impacto de mercado.
- Thresholds não são recomendações operacionais.
- A camada é diagnóstica e deve continuar paralela ao ranking padrão até haver validação robusta.
