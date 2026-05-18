# Histórico da Cadeia de Opções

## Objetivo

O histórico da cadeia de opções salva snapshots por data para permitir análises posteriores de liquidez, moneyness, vencimento, spread, Greeks aproximados e estruturas.

Essa camada não altera o score de ações, não executa ordens e não transforma estruturas em recomendação. Ela apenas prepara dados históricos para estudo.

## Construir Histórico

```powershell
python -m src.scanners.options_history_builder --start 2026-01-02 --end 2026-04-30 --underlyings PETR4 VALE3 ITUB4 --save-db --csv
```

O comando procura opções disponíveis no SQLite/COTAHIST processado, normaliza a cadeia, calcula métricas e salva snapshots históricos.

Se não houver dados para o período ou ativos, o comando retorna diagnóstico claro e não quebra:

```text
Não foram encontrados dados históricos de cadeia de opções para o período/ativos informados.
```

## Cobertura

A cobertura é classificada como:

- `SEM_DADOS`;
- `COBERTURA_FRACA`;
- `COBERTURA_MEDIA`;
- `COBERTURA_BOA`.

Essa classificação considera quantidade de datas, opções, ativos e snapshots. Backtests de opções com `SEM_DADOS` ou `COBERTURA_FRACA` devem permanecer exploratórios.

## Limitações

O histórico depende da qualidade da cadeia disponível. Sem bid/ask, strikes, vencimentos e liquidez por data, o backtest pode ficar incompleto ou ser bloqueado por dados insuficientes.

