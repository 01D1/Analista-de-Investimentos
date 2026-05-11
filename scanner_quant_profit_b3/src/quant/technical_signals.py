"""
Technical signals — interpreta indicadores técnicos a partir de OHLCV.
Retorna dict estruturado com sinal, valor e interpretação por indicador.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import ema, rsi, macd, atr, bollinger_bands, sma


def compute_signals(df: pd.DataFrame) -> dict:
    """
    Args:
        df: OHLCV com colunas open,high,low,close,volume (ordem crescente de data).

    Returns:
        {
          signals: list of {name, value, direction, interpretation, color, score?}
          overall: {direction, score, label, color}
          stats:   {price, atr, atr_pct, bb_width, rsi, macd_hist, vol_ratio}
        }
    """
    _empty = {
        "signals": [],
        "overall": {"direction": "NEUTRO", "score": 50, "label": "Dados insuficientes", "color": "#64748B"},
        "stats": {},
    }
    if df is None or df.empty or len(df) < 30:
        return _empty

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]
    price  = float(close.iloc[-1])

    signals = []
    scored: list[float] = []

    # ── EMA Trend ──────────────────────────────────────────────────────────
    e9_s   = ema(close, 9)
    e21_s  = ema(close, 21)
    e200_s = ema(close, 200)
    e9    = float(e9_s.iloc[-1])
    e21   = float(e21_s.iloc[-1])
    e200  = float(e200_s.iloc[-1])
    e9_p  = float(e9_s.iloc[-2])
    e21_p = float(e21_s.iloc[-2])

    emas_above = sum([price > e9, price > e21, price > e200])
    golden = (e9 > e21) and (e9_p <= e21_p)
    death  = (e9 < e21) and (e9_p >= e21_p)

    if emas_above == 3:
        t_dir, t_color, t_score = "ALTA", "#22C55E", 80
        t_text = "Acima das 3 EMAs — tendência de alta sólida"
    elif emas_above == 2:
        t_dir, t_color, t_score = "ALTA_MOD", "#86EFAC", 65
        t_text = "Acima de 2/3 EMAs — momentum positivo"
    elif emas_above == 1:
        t_dir, t_color, t_score = "BAIXA_MOD", "#FCA5A5", 35
        t_text = "Abaixo de 2/3 EMAs — momentum negativo"
    else:
        t_dir, t_color, t_score = "BAIXA", "#EF4444", 20
        t_text = "Abaixo das 3 EMAs — tendência de baixa"

    if golden:
        t_text += " · Golden Cross (9/21)"
    elif death:
        t_text += " · Death Cross (9/21)"

    signals.append({
        "name": "Tendência (EMAs)",
        "value": f"vs E9 {(price/e9-1)*100:+.1f}% · vs E200 {(price/e200-1)*100:+.1f}%",
        "direction": t_dir, "interpretation": t_text, "color": t_color, "score": t_score,
    })
    scored.append(t_score)

    # ── RSI ────────────────────────────────────────────────────────────────
    rsi_s   = rsi(close, 14)
    rsi_now = float(rsi_s.iloc[-1])
    rsi_prv = float(rsi_s.iloc[-2])

    if rsi_now >= 70:
        r_dir, r_color, r_score = "OVERBOUGHT", "#EF4444", 25
        r_text = f"RSI {rsi_now:.1f} — sobrecomprado, cautela com novas compras"
    elif rsi_now >= 60:
        r_dir, r_color, r_score = "ALTA", "#22C55E", 70
        r_text = f"RSI {rsi_now:.1f} — força, viés comprador saudável"
    elif rsi_now >= 50:
        r_dir, r_color, r_score = "NEUTRO_ALTA", "#86EFAC", 60
        r_text = f"RSI {rsi_now:.1f} — acima do equilíbrio"
    elif rsi_now >= 40:
        r_dir, r_color, r_score = "NEUTRO_BAIXA", "#FCA5A5", 40
        r_text = f"RSI {rsi_now:.1f} — abaixo do equilíbrio"
    elif rsi_now >= 30:
        r_dir, r_color, r_score = "BAIXA", "#EF4444", 30
        r_text = f"RSI {rsi_now:.1f} — fraqueza, pressão vendedora"
    else:
        r_dir, r_color, r_score = "OVERSOLD", "#22C55E", 75
        r_text = f"RSI {rsi_now:.1f} — sobrevendido, possível reversão técnica"

    trend_tag = " (subindo)" if rsi_now > rsi_prv and 30 < rsi_now < 70 else \
                " (caindo)"  if rsi_now < rsi_prv and 30 < rsi_now < 70 else ""
    r_text += trend_tag

    signals.append({
        "name": "RSI (14)",
        "value": f"{rsi_now:.1f}",
        "direction": r_dir, "interpretation": r_text, "color": r_color, "score": r_score,
    })
    scored.append(r_score)

    # ── MACD ───────────────────────────────────────────────────────────────
    ml_s, sl_s, hist_s = macd(close, 12, 26, 9)
    ml_now   = float(ml_s.iloc[-1])
    sig_now  = float(sl_s.iloc[-1])
    hist_now = float(hist_s.iloc[-1])
    ml_prv   = float(ml_s.iloc[-2])
    sig_prv  = float(sl_s.iloc[-2])
    hist_prv = float(hist_s.iloc[-2])

    cross_up   = (ml_now > sig_now) and (ml_prv <= sig_prv)
    cross_down = (ml_now < sig_now) and (ml_prv >= sig_prv)
    hist_exp   = abs(hist_now) > abs(hist_prv)

    if ml_now > sig_now and hist_now > 0:
        m_dir, m_color, m_score = "ALTA", "#22C55E", 75
        m_text = "MACD bullish — linha acima do sinal, histograma positivo"
    elif ml_now > sig_now:
        m_dir, m_color, m_score = "ALTA_MOD", "#86EFAC", 60
        m_text = "MACD bullish moderado — linha acima, histograma ainda negativo"
    elif ml_now < sig_now and hist_now < 0:
        m_dir, m_color, m_score = "BAIXA", "#EF4444", 25
        m_text = "MACD bearish — linha abaixo do sinal, histograma negativo"
    else:
        m_dir, m_color, m_score = "BAIXA_MOD", "#FCA5A5", 40
        m_text = "MACD bearish moderado — possível reversão"

    if cross_up:
        m_text += " · Cruzamento bullish!"
    elif cross_down:
        m_text += " · Cruzamento bearish!"
    if hist_exp:
        m_text += " · momentum expandindo"

    signals.append({
        "name": "MACD (12/26/9)",
        "value": f"Hist {hist_now:+.3f}",
        "direction": m_dir, "interpretation": m_text, "color": m_color, "score": m_score,
    })
    scored.append(m_score)

    # ── Bollinger Bands ───────────────────────────────────────────────────
    upper_s, mid_s, lower_s = bollinger_bands(close, 20, 2.0)
    bb_upper = float(upper_s.iloc[-1])
    bb_mid   = float(mid_s.iloc[-1])
    bb_lower = float(lower_s.iloc[-1])
    bb_range = bb_upper - bb_lower
    bb_width = bb_range / bb_mid if bb_mid > 0 else 0
    bb_pct   = (price - bb_lower) / bb_range if bb_range > 0 else 0.5

    # Bandwidth z-score para detectar squeeze
    bw_series = ((upper_s - lower_s) / mid_s).dropna()
    bw_z = float((bb_width - bw_series.mean()) / bw_series.std()) if bw_series.std() > 0 else 0

    if price > bb_upper:
        b_dir, b_color, b_score = "OVERBOUGHT", "#EF4444", 30
        b_text = "Acima da banda superior — extensão de alta, risco de reversão"
    elif price < bb_lower:
        b_dir, b_color, b_score = "OVERSOLD", "#22C55E", 70
        b_text = "Abaixo da banda inferior — extensão de baixa, potencial de reversão"
    elif bb_pct > 0.75:
        b_dir, b_color, b_score = "ALTA", "#86EFAC", 65
        b_text = f"%B={bb_pct:.2f} — zona alta das bandas"
    elif bb_pct < 0.25:
        b_dir, b_color, b_score = "BAIXA", "#FCA5A5", 35
        b_text = f"%B={bb_pct:.2f} — zona baixa das bandas"
    else:
        b_dir, b_color, b_score = "NEUTRO", "#64748B", 50
        b_text = f"%B={bb_pct:.2f} — região central"

    if bw_z < -1.0:
        b_text += " · Squeeze ativo (compressão de volatilidade)"

    signals.append({
        "name": "Bollinger Bands (20,2)",
        "value": f"%B {bb_pct:.2f} · BW {bb_width:.2%}",
        "direction": b_dir, "interpretation": b_text, "color": b_color, "score": b_score,
    })
    scored.append(b_score)

    # ── ATR (informativo — não pontua direção) ────────────────────────────
    atr_s   = atr(high, low, close, 14)
    atr_now = float(atr_s.iloc[-1])
    atr_pct = atr_now / price * 100 if price > 0 else 0

    if atr_pct > 4:
        atr_regime, atr_color = "Vol Alta", "#EF4444"
    elif atr_pct > 2:
        atr_regime, atr_color = "Vol Moderada", "#F59E0B"
    else:
        atr_regime, atr_color = "Vol Baixa", "#22C55E"

    signals.append({
        "name": "ATR (14)",
        "value": f"R${atr_now:.2f} ({atr_pct:.1f}%)",
        "direction": atr_regime,
        "interpretation": (
            f"ATR = {atr_pct:.1f}% do preço · {atr_regime} · "
            f"Stop 2×ATR: R${price - 2*atr_now:.2f}"
        ),
        "color": atr_color,
        "score": None,
    })

    # ── Volume ────────────────────────────────────────────────────────────
    vol_sma  = float(sma(volume, 20).iloc[-1])
    vol_now  = float(volume.iloc[-1])
    vol_ratio = vol_now / vol_sma if vol_sma > 0 else 1.0

    if vol_ratio > 2.0:
        v_color = "#3B82F6"
        v_text = f"{vol_ratio:.1f}× a média — aumento expressivo de participação"
    elif vol_ratio > 1.3:
        v_color = "#60A5FA"
        v_text = f"{vol_ratio:.1f}× a média — acima do normal"
    elif vol_ratio > 0.7:
        v_color = "#64748B"
        v_text = f"{vol_ratio:.1f}× a média — volume normal"
    else:
        v_color = "#334155"
        v_text = f"{vol_ratio:.1f}× a média — abaixo do normal, pouca participação"

    signals.append({
        "name": "Volume",
        "value": f"{vol_ratio:.1f}× média",
        "direction": "INFO",
        "interpretation": v_text,
        "color": v_color,
        "score": None,
    })

    # ── Overall ───────────────────────────────────────────────────────────
    avg = float(np.mean(scored)) if scored else 50.0

    if avg >= 70:
        ov_dir, ov_color, ov_label = "ALTA", "#22C55E", "Viés Comprador Forte"
    elif avg >= 60:
        ov_dir, ov_color, ov_label = "ALTA_MOD", "#86EFAC", "Viés Comprador Moderado"
    elif avg >= 50:
        ov_dir, ov_color, ov_label = "NEUTRO", "#64748B", "Neutro / Indefinido"
    elif avg >= 40:
        ov_dir, ov_color, ov_label = "BAIXA_MOD", "#FCA5A5", "Viés Vendedor Moderado"
    else:
        ov_dir, ov_color, ov_label = "BAIXA", "#EF4444", "Viés Vendedor Forte"

    return {
        "signals": signals,
        "overall": {"direction": ov_dir, "score": round(avg, 1), "label": ov_label, "color": ov_color},
        "stats": {
            "price": price,
            "atr": atr_now,
            "atr_pct": atr_pct,
            "bb_width": bb_width,
            "rsi": rsi_now,
            "macd_hist": hist_now,
            "vol_ratio": vol_ratio,
        },
    }
