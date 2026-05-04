# Robô em tempo real: Profit Pro → Excel → Python

## 1. Estrutura de pastas sugerida no Windows

```text
C:\scanner_quant\
├── data\
│   ├── realtime\
│   │   └── RTD PROFIT.xlsx
│   ├── database\
│   ├── raw\
│   └── reports\
├── src\
├── config.yaml
└── requirements.txt
```

Coloque sua planilha do Profit em:

```text
C:\scanner_quant\data\realtime\RTD PROFIT.xlsx
```

## 2. Ajustar config.yaml

Confirme se está assim:

```yaml
profit_excel_path: "C:/scanner_quant/data/realtime/RTD PROFIT.xlsx"
profit_sheet_name: "Planilha1"
```

## 3. Instalar dependências

```powershell
cd C:\scanner_quant
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Criar o banco

```powershell
python -m src.db.init_db
```

## 5. Abrir Profit e Excel

Antes de rodar o robô:

1. Abra o Profit Pro.
2. Abra a planilha RTD no Excel.
3. Confirme que os valores estão atualizando.
4. Mantenha o Excel aberto.

## 6. Testar uma leitura única

```powershell
python -m src.scanners.realtime_profit_scanner --once --top 10 --csv
```

## 7. Rodar continuamente

```powershell
python -m src.scanners.realtime_profit_scanner --interval 5 --top 10
```

Para parar, use `CTRL+C`.

## O que o robô faz

A cada rodada, ele:

1. lê a planilha do Profit;
2. normaliza os dados;
3. salva snapshots no SQLite;
4. calcula métricas intraday;
5. gera score de 0 a 100;
6. classifica como `COMPRA/FORÇA`, `OBSERVAR`, `NEUTRO` ou `FRAQUEZA`;
7. salva sinais no banco.

## Observação

Esse robô não envia ordens. Ele é um scanner/alerta para apoiar decisão operacional.
