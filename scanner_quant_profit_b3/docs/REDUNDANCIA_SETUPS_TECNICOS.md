# Redundância de Setups Técnicos

Um mesmo ativo em uma mesma data pode disparar vários setups correlatos. Isso infla a amostra e pode dar impressão falsa de robustez.

## Grupos de equivalência

Momentum:

- `BREAKOUT_VOLUME`
- `MOMENTUM_CONTINUATION`
- `RANGE_EXPANSION`
- `RELATIVE_STRENGTH_LEADER`

Reversão:

- `MEAN_REVERSION`
- `OVERSOLD_REVERSAL`

Tendência:

- `PULLBACK_TREND`
- `VWAP_RECLAIM`

## Regra

Para mesmo ticker, data, direção e grupo, mantém-se o setup com maior score e maior confiança. Os setups removidos ficam registrados no metadata do evento canônico.

