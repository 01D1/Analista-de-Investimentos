# Modelos de Volatilidade

A Fase 29 adiciona múltiplas estimativas de volatilidade:

- `vol_5d`, `vol_10d`, `vol_20d`, `vol_60d`, `vol_252d`: fechamento a fechamento anualizado;
- `vol_ewma`: EWMA com lambda padrão 0,94;
- `downside_vol`: volatilidade apenas dos retornos negativos;
- `parkinson_vol`: usa máxima e mínima;
- `garman_klass_vol`: usa abertura, máxima, mínima e fechamento;
- `atr_vol`: ATR dividido pelo preço;
- `ensemble_vol`: média das volatilidades disponíveis.

Regimes:

- `VOL_BAIXA`
- `VOL_NORMAL`
- `VOL_ALTA`
- `VOL_EXTREMA`
- `VOL_EXPANDINDO`
- `VOL_COMPRIMINDO`
- `DADOS_INSUFICIENTES`

As classificações servem para governança e explicação. Não alteram ranking principal.
