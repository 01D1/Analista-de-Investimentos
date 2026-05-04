# Módulo de Conexão Ações + Opções

## Arquivo criado

Copie este arquivo para o seu projeto:

```text
src/scanners/combined_stock_options_scanner.py
```

## Pasta usada para relatórios

O script salva relatórios em:

```text
data/reports/
```

Se a pasta não existir, o próprio script cria automaticamente.

## Como rodar

1. Primeiro rode o scanner de ações:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10
```

Fora do pregão, para teste:

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo
```

2. Depois rode a coleta da B3:

```powershell
python -m src.collectors.b3_cotahist_collector --year 2026
```

3. Agora rode o ranking combinado:

```powershell
python -m src.scanners.combined_stock_options_scanner --min-volume 100000 --min-trades 10 --top 30
```

Com relatório CSV:

```powershell
python -m src.scanners.combined_stock_options_scanner --min-volume 100000 --min-trades 10 --top 30 --csv
```

## Lógica do ranking

Score final = 60% score da ação + 40% score da opção.

A primeira versão prioriza:
- força da ação;
- volume da opção;
- quantidade de negócios;
- preço válido;
- strike válido;
- quantidade negociada.
