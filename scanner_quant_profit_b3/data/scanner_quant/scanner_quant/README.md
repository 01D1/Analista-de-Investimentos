# Scanner Quant Profit + B3 - v2

## Instalação

```powershell
python -m pip install -r requirements.txt
python -m src.db.init_db
```

## Planilha do Profit

Coloque a planilha aqui:

```text
data/realtime/RTD PROFIT.xlsx
```

No `config.yaml`:

```yaml
profit_excel_path: "data/realtime/RTD PROFIT.xlsx"
profit_sheet_name: "Planilha1"
```

## Scanner Profit com dados reais

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10
```

## Scanner em modo demo fora do pregão

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --demo
```

## Rodar contínuo

```powershell
python -m src.scanners.realtime_profit_scanner --interval 5 --top 10
```

## Baixar e processar B3 COTAHIST

```powershell
python -m src.collectors.b3_cotahist_collector --year 2026
```

Todos os anos do config:

```powershell
python -m src.collectors.b3_cotahist_collector --all
```

## Scanner inicial de opções

```powershell
python -m src.scanners.b3_options_scanner --min-volume 100000 --min-trades 10 --top 30
```
