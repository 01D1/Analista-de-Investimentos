# Indicadores Técnicos

Os indicadores ficam em `src/technical/indicators.py` e são funções puras sobre `pandas.Series`.

Indicadores disponíveis:

- SMA e EMA;
- RSI;
- MACD;
- ATR;
- Bollinger Bands;
- Donchian Channels;
- ADX aproximado;
- VWAP acumulado;
- z-score móvel;
- distância da média;
- rate of change;
- volume relativo.

As funções toleram séries curtas e dados ausentes. Quando não há informação suficiente, retornam `NaN`, valores neutros ou séries vazias sem quebrar o pipeline.

