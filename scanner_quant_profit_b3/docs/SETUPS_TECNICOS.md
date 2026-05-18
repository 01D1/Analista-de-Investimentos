# Setups Técnicos

Os setups são regras objetivas e parametrizadas em `src/technical/setups.py`.

Setups iniciais:

- `BREAKOUT_VOLUME`
- `BREAKDOWN_VOLUME`
- `PULLBACK_TREND`
- `MEAN_REVERSION`
- `MOMENTUM_CONTINUATION`
- `VOLATILITY_SQUEEZE`
- `VWAP_RECLAIM`
- `RELATIVE_STRENGTH_LEADER`
- `OVERSOLD_REVERSAL`
- `RANGE_EXPANSION`

Cada setup retorna data, ticker, tipo, score, confiança, direção, preço de gatilho, invalidação, alvo indicativo, risco indicativo, motivos favoráveis e motivos contrários.

Esses campos documentam um padrão a investigar. O sistema não executa ordens e não recomenda compra ou venda.

