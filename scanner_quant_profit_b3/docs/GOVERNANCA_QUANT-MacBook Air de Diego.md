# Governança Quant

## Objetivo

A governança quantitativa impede que scores, filtros, thresholds ou setups sejam promovidos a candidatos operacionais sem evidência mínima de robustez.

Ela não opera, não altera score, não altera ranking, não muda pesos e não aplica thresholds automaticamente. A função é classificar, aprovar, rejeitar ou colocar candidatos em observação.

## Por Que Existe

Um backtest bom dentro da amostra pode ser resultado de overfitting. Uma combinação de filtros pode melhorar o retorno líquido no passado e falhar fora da amostra.

Por isso, a governança exige:

- validação fora da amostra;
- amostra mínima;
- janelas suficientes;
- retorno líquido positivo;
- hit rate mínimo;
- concentração aceitável;
- liquidez operacional;
- ausência de alerta de overfitting.

## Status

Os status possíveis são:

- `EXPERIMENTAL`;
- `EM_OBSERVACAO`;
- `PROMISSOR`;
- `CANDIDATO_OPERACIONAL`;
- `REJEITADO`;
- `BLOQUEADO_OVERFITTING`;
- `AMOSTRA_INSUFICIENTE`;
- `CONCENTRACAO_EXCESSIVA`;
- `LIQUIDEZ_INSUFICIENTE`.
- `CANDIDATO_RESTRITO_A_REGIME`;
- `BLOQUEADO_REGIME_INSUFICIENTE`;
- `BLOQUEADO_REGIME_RISCO`.
- `CANDIDATO_EVENT_DRIVEN`;
- `BLOQUEADO_EVENTO_INSUFICIENTE`;
- `BLOQUEADO_EVENTO_CONTRA_SINAL`.
- `BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE`.
- `BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE`.

`CANDIDATO_OPERACIONAL` é o único status aprovado. Mesmo assim, ele apenas libera o candidato para estudo operacional; não executa ordens nem muda o scanner.

## Critérios Padrão

Para candidato operacional:

- pelo menos 6 janelas;
- pelo menos 60% de janelas positivas;
- retorno líquido médio de teste acima de zero;
- hit rate médio de pelo menos 52%;
- concentração top 3 ativos até 50%;
- pelo menos 300 sinais;
- sem overfitting;
- sem alerta de amostra, concentração ou liquidez;
- degradação treino/teste aceitável.

## Bloqueios

`BLOQUEADO_OVERFITTING` aparece quando:

- há alerta explícito de overfitting;
- treino positivo e teste negativo;
- robustez classificada como `OVERFIT_PROVAVEL`;
- degradação treino/teste é alta.

`AMOSTRA_INSUFICIENTE` aparece quando faltam janelas, sinais ou histórico.

`CONCENTRACAO_EXCESSIVA` aparece quando poucos ativos explicam demais o resultado.

`LIQUIDEZ_INSUFICIENTE` aparece quando a execução média é ruim, inviável ou há alerta de liquidez.

## Governança Por Regime

Um candidato pode passar no agregado e ainda assim falhar em regimes específicos.

Nesses casos:

- `CANDIDATO_RESTRITO_A_REGIME`: só deve ser estudado nos regimes permitidos;
- `BLOQUEADO_REGIME_INSUFICIENTE`: poucos regimes ou pouca amostra;
- `BLOQUEADO_REGIME_RISCO`: perda líquida relevante em regimes testados.

Comando de suporte:

```powershell
python -m src.scanners.regime_analysis --start 2026-01-02 --end 2026-04-30 --save-db --csv
```

## Governança Com Eventos

Eventos entram como contexto explicativo adicional. A governança pode classificar:

- `CANDIDATO_EVENT_DRIVEN`: o resultado positivo aparece principalmente em sinais com evento;
- `BLOQUEADO_EVENTO_INSUFICIENTE`: a base de eventos ainda e pequena;
- `BLOQUEADO_EVENTO_CONTRA_SINAL`: eventos contrários ao sinal pioram a estatística.
- `BLOQUEADO_COBERTURA_EVENTOS_INSUFICIENTE`: a cobertura de eventos ainda não permite conclusão forte.
- `BLOQUEADO_COBERTURA_REGIME_INSUFICIENTE`: a cobertura de eventos é fraca em um ou mais regimes, impedindo conclusão forte naquele ambiente.

Essa leitura impede que um setup técnico seja tratado como robusto quando, na verdade, depende de resultado, fato relevante, evento macro ou commodity.

Comandos:

```powershell
python -m src.scanners.import_market_events --csv data/events/market_events.csv --save-db
python -m src.scanners.event_pipeline --start 2026-01-02 --end 2026-04-30 --sources csv --csv-path data/events/market_events_example.csv --save-db --csv
python -m src.scanners.event_daily_update --start 2026-01-02 --end 2026-04-30 --save-db --csv --with-regimes
python -m src.scanners.source_health_check --save-db --csv
python -m src.scanners.daily_quant_routine --start 2026-01-02 --end 2026-04-30 --with-regimes --with-event-context --with-governance --save-db --csv
python -m src.scanners.event_context_analysis --start 2026-01-02 --end 2026-04-30 --csv --save-db
```

Health checks e alertas operacionais não aprovam candidatos. Eles apenas reduzem o risco de interpretar ausência de dados como ausência de evento.

## Governança De Opções

Opções e estruturas possuem governança própria. Os status principais são:

- `OPTION_APPROVED_FOR_STUDY`;
- `OPTION_OBSERVATION_ONLY`;
- `OPTION_BLOCKED_LIQUIDITY`;
- `OPTION_BLOCKED_SPREAD`;
- `OPTION_BLOCKED_EXPIRY`;
- `OPTION_BLOCKED_DATA`;
- `OPTION_BLOCKED_RISK`;
- `STRUCTURE_APPROVED_FOR_STUDY`;
- `STRUCTURE_OBSERVATION_ONLY`;
- `STRUCTURE_BLOCKED_RISK`;
- `STRUCTURE_BLOCKED_LIQUIDITY`;
- `STRUCTURE_BLOCKED_DATA`.

`APPROVED_FOR_STUDY` significa apenas que a opção ou estrutura pode ser analisada com mais detalhe. Não é recomendação, não executa ordem e não altera o ranking principal de ações.

Comando:

```powershell
python -m src.scanners.options_intelligence_scanner --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

Backtests preliminares de estruturas recebem status próprios:

- `OPTIONS_BACKTEST_PROMISSOR`;
- `OPTIONS_BACKTEST_EM_OBSERVACAO`;
- `OPTIONS_BACKTEST_REJEITADO`;
- `OPTIONS_BACKTEST_BLOQUEADO_DADOS`;
- `OPTIONS_BACKTEST_BLOQUEADO_EXECUCAO`;
- `OPTIONS_BACKTEST_BLOQUEADO_AMOSTRA`.

Comando:

```powershell
python -m src.scanners.options_structure_backtest --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --save-db --csv
```

Governança fora da amostra de opções usa o walk-forward:

```powershell
python -m src.scanners.options_walk_forward_analysis --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --structure LONG_CALL --train-months 3 --test-months 1 --save-db --csv
```

## Comando

Para revisar o último walk-forward dos filtros:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --save-db
```

Também é possível revisar:

```powershell
python -m src.scanners.governance_review --source walk_forward --latest --save-db
python -m src.scanners.governance_review --source historical_backtest --latest --save-db
python -m src.scanners.governance_review --source threshold_optimization --latest --save-db
```

Parâmetros úteis:

```powershell
python -m src.scanners.governance_review --source filter_walk_forward --latest --min-windows 6 --min-signals 300 --min-positive-windows-pct 60 --max-concentration-pct 50 --save-db
```

## Persistência

Os reviews são salvos em:

- `governance_reviews`.

Campos principais:

- fonte;
- run de origem;
- candidato;
- status;
- aprovado ou não;
- risco;
- confiança;
- motivos favoráveis;
- motivos contrários;
- ações necessárias.

## Mesa Quant

A aba `Governança Quant` mostra:

- últimos reviews;
- status dos candidatos;
- aprovado/não aprovado;
- risco;
- confiança;
- motivos e ações;
- contagem por status;
- status por regime e por evento, quando existir;
- alertas de overfitting, amostra, concentração e liquidez.

## Governança Técnica

A camada técnica possui governança própria em `src/technical/technical_governance.py`.

Ela classifica setups como:

- `TECH_APPROVED_FOR_STUDY`;
- `TECH_OBSERVATION_ONLY`;
- `TECH_BLOCKED_INSUFFICIENT_DATA`;
- `TECH_BLOCKED_HIGH_VOLATILITY`;
- `TECH_BLOCKED_NEGATIVE_NET_RETURN`.

Mesmo quando um setup é aprovado para estudo, ele não é promovido a operação e não altera o score/ranking principal.

## Interpretação

Um candidato `PROMISSOR` ainda não deve ser promovido. Ele apenas merece mais testes.

Um candidato `BLOQUEADO_OVERFITTING` deve permanecer rejeitado até nova validação com mais histórico, múltiplos regimes e menor sensibilidade a thresholds.

Um candidato `CANDIDATO_OPERACIONAL` ainda não é recomendação. Ele apenas passou pelos critérios mínimos de governança.
