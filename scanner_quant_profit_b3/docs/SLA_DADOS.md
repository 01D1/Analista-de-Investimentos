# SLA Dos Dados

## Objetivo

O SLA dos dados mede a confiabilidade historica das fontes que alimentam a camada de eventos. Ele responde se a fonte estava disponivel, se tinha registros, se estava atualizada e se vem falhando de forma recorrente.

Essa camada nao altera score, ranking, pesos ou filtros. Ela serve para impedir conclusoes fortes quando a base de contexto esta incompleta.

## Metricas Por Fonte

Para cada fonte monitorada, o sistema calcula:

- total de checks;
- percentual de disponibilidade;
- percentual de status `OK`, `WARNING`, `ERROR`, `MISSING`, `STALE` e `EMPTY`;
- idade media e maxima dos dados;
- ultimo status;
- ultima data com status `OK`;
- dias desde o ultimo `OK`;
- classe de confiabilidade.

## Classes De Confiabilidade

- `EXCELENTE`: fonte muito disponivel, com poucos erros e baixa defasagem;
- `BOA`: fonte utilizavel, com falhas pequenas;
- `INSTAVEL`: fonte ainda disponivel, mas com alertas recorrentes;
- `RUIM`: fonte exige revisao antes de conclusoes fortes;
- `CRITICA`: fonte ausente, com erro recorrente ou disponibilidade muito baixa;
- `SEM_DADOS`: nao ha historico suficiente.

## Comando

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

O comando le `source_health_checks`, calcula SLA por fonte, salva snapshots e gera CSVs em `data/reports`.

Para revisar crescimento das tabelas operacionais sem apagar nada:

```powershell
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
```

## Persistencia

Os snapshots sao gravados em:

- `source_sla_snapshots`: uma linha por fonte e janela;
- `operational_observability_snapshots`: resumo geral da operacao.

Essas tabelas permitem observar se uma fonte melhora, piora ou fica instavel ao longo do tempo.

## Interpretacao

Uma fonte `CRITICA` ou `RUIM` nao invalida automaticamente o scanner quantitativo, mas limita a interpretacao de eventos. Por exemplo: se News Hunter esta `STALE`, a ausencia de noticia em um sinal nao deve ser lida como ausencia real de noticia.

## Limites

- O SLA depende da rotina de health check ser executada periodicamente.
- A janela padrao de 30 dias pode ser curta para fontes pouco frequentes.
- Fontes locais podem ficar boas tecnicamente, mas ainda ter baixa cobertura de mercado.
- Retenção e limpeza devem começar sempre por dry-run; execução real exige confirmação explícita.
