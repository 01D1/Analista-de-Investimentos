# Saúde Das Fontes

## Objetivo

A camada de saúde das fontes verifica se as bases locais que alimentam eventos estão disponíveis, têm registros e foram atualizadas recentemente. Ela serve para evitar conclusões fortes quando a ausência de notícia é, na verdade, ausência de dados.

## Fontes Monitoradas

- CSV manual de eventos;
- News Hunter local;
- calendário econômico local;
- índices CVM/IPE processados;
- releases/eventos qualitativos locais.

## Status

- `OK`: fonte disponível, com registros e data recente;
- `WARNING`: fonte disponível, mas com baixa quantidade ou leve atraso;
- `ERROR`: erro de leitura ou schema inválido;
- `MISSING`: arquivo, pasta ou banco ausente;
- `STALE`: fonte existe, mas está antiga;
- `EMPTY`: fonte existe, mas sem registros;
- `UNKNOWN`: estado não determinado.

## Comando

```powershell
python -m src.scanners.source_health_check --save-db --csv
```

Depois de acumular checks, calcule o SLA historico:

```powershell
python -m src.scanners.operational_observability --window-days 30 --save-db --csv
```

Com falha explícita para automações:

```powershell
python -m src.scanners.source_health_check --save-db --csv --fail-on-error
```

## Saídas

- tabela `source_health_checks`;
- tabela `source_sla_snapshots`, quando a observabilidade operacional for executada;
- CSV `source_health_checks_YYYYMMDD_HHMMSS.csv`;
- resumo no terminal.

## Interpretação

Se uma fonte está `MISSING`, `ERROR`, `EMPTY` ou `STALE`, a análise evento x sem evento deve ser lida com cautela. O sistema não altera score ou ranking; ele apenas registra o risco operacional da base de contexto.

O SLA historico adiciona a dimensao de recorrencia: uma falha isolada pode ser apenas warning, mas falhas repetidas classificam a fonte como `INSTAVEL`, `RUIM` ou `CRITICA`.
