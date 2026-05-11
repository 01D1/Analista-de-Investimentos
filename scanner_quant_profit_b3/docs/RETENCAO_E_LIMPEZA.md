# Retenção E Limpeza Segura

## Objetivo

A camada de retenção controla o crescimento das tabelas operacionais sem apagar dados por acidente. Ela avalia linhas antigas, permite dry-run, arquiva antes de deletar e respeita uma lista de tabelas protegidas.

Ela não altera score, ranking, pesos, filtros ou qualquer lógica quantitativa.

## Política

A política fica em `config/retention.yaml` e define:

- dias de retenção por tabela;
- diretório de archive;
- formato de archive;
- dry-run como padrão;
- exigência de confirmação para deletar;
- tabelas que nunca devem ser removidas.

## Dry-run

Use sempre primeiro:

```powershell
python -m src.scanners.data_retention_cleanup --dry-run --save-db --csv
```

O dry-run calcula linhas candidatas, mas não remove nada e não arquiva nada.

## Execução Real

Execução real exige confirmação explícita:

```powershell
python -m src.scanners.data_retention_cleanup --execute --confirm --archive --save-db --csv
```

Sem `--confirm`, a execução real é bloqueada e o comando volta para dry-run.

## Persistência

As execuções são salvas em:

- `retention_cleanup_runs`;
- `retention_cleanup_details`.

Os detalhes mostram tabela, data de corte, linhas candidatas, linhas arquivadas, linhas deletadas e status.

## Tabelas Protegidas

Tabelas protegidas não são deletadas pela rotina, mesmo se aparecerem na política. A configuração padrão protege bases históricas e dados de eventos brutos.

## Limitações

- A limpeza atua apenas em tabelas com coluna temporal mapeada.
- Archive em CSV preserva linhas removidas, mas não substitui backup completo do banco.
- Use execução real apenas depois de revisar o dry-run.
