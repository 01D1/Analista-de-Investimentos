# Como rodar no Windows

1. Crie a pasta:

```powershell
mkdir C:\scanner_quant
```

2. Copie o projeto para essa pasta.

3. Coloque sua planilha RTD em:

```text
C:\scanner_quant\RTD PROFIT.xlsx
```

4. Abra o Profit Pro e o Excel. Confirme que a planilha está atualizando.

5. No terminal dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m src.db.init_db
python -m src.collectors.profit_excel_collector
```

Em outro terminal:

```powershell
python -m src.scanners.stock_scanner
```
