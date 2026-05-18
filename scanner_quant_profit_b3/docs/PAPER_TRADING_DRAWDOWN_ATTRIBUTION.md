# Drawdown Attribution no Paper Trading

A atribuicao de drawdown identifica periodos em que a curva de equity simulada ficou abaixo do pico anterior e estima quais ativos contribuíram para a perda.

Campos principais:

- inicio do drawdown;
- fundo do drawdown;
- recuperacao, quando houver;
- profundidade;
- duracao;
- contribuicao por ticker.

Uso:

```powershell
python -m src.scanners.paper_fragility_analysis --paper-run-id 1 --save-db --csv
```

A leitura deve ser usada para investigacao. Drawdown attribution nao e stop operacional e nao implica ordem real.
