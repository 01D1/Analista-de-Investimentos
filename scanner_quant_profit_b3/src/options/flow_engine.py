"""
Flow Engine — Leitura de fluxo simplificada (Times & Trades proxy).

Identifica agressão compradora/vendedora usando:
  - Variação de preço (direção)
  - Aceleração de volume vs média
  - Aceleração de negócios vs média

flow_score  : -100 (venda extrema) → +100 (compra extrema)
classification: FORTE_VENDA | VENDA | NEUTRO | COMPRA | FORTE_COMPRA
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


# ── Resultado ────────────────────────────────────────────────────────────────

@dataclass
class FlowResult:
    classification: str       # FORTE_COMPRA … FORTE_VENDA
    score: float              # -100 a +100
    intensity: float          # 0.0 a 1.0 (abs(score)/100)
    buy_pressure: float       # 0.0 a 1.0
    sell_pressure: float      # 0.0 a 1.0
    volume_ratio: float       # vol atual / média
    trades_ratio: float       # trades atual / média
    price_direction: str      # ALTA | BAIXA | LATERAL
    explanation: str


_CLS_MAP = {
    "FORTE_COMPRA": ("FORTE COMPRA",  "#22C55E", "🟢"),
    "COMPRA":       ("COMPRA",         "#4ADE80", "🟩"),
    "NEUTRO":       ("NEUTRO",         "#64748B", "⬜"),
    "VENDA":        ("VENDA",          "#F87171", "🟥"),
    "FORTE_VENDA":  ("FORTE VENDA",   "#EF4444", "🔴"),
}


def compute_flow(df: pd.DataFrame, window: int = 20) -> FlowResult:
    """
    Computa o flow score a partir de um DataFrame OHLCV diário.

    df deve conter: close, volume, trades (ou quantity)
    """
    if df.empty or len(df) < 3:
        return _neutral("Dados insuficientes.")

    df = df.copy().reset_index(drop=True)
    close  = pd.to_numeric(df["close"],  errors="coerce").fillna(method="ffill")
    volume = pd.to_numeric(df.get("volume",   pd.Series([0]*len(df))), errors="coerce").fillna(0)
    trades = pd.to_numeric(df.get("trades",   pd.Series([0]*len(df))), errors="coerce").fillna(0)

    n = min(window, len(df))

    # ── Médias de referência ────────────────────────────────────────────────
    avg_vol    = volume.iloc[-n:].mean()   if avg_safe(volume) else 1.0
    avg_trades = trades.iloc[-n:].mean()   if avg_safe(trades) else 1.0

    last_vol    = float(volume.iloc[-1])
    last_trades = float(trades.iloc[-1])
    last_close  = float(close.iloc[-1])
    prev_close  = float(close.iloc[-2]) if len(close) > 1 else last_close

    vol_ratio    = last_vol    / avg_vol    if avg_vol    > 0 else 1.0
    trades_ratio = last_trades / avg_trades if avg_trades > 0 else 1.0

    # ── Variação de preço (5 períodos) ─────────────────────────────────────
    ref_close  = float(close.iloc[max(-6, -len(close))])
    price_chg  = (last_close / ref_close - 1.0) * 100.0 if ref_close > 0 else 0.0

    price_dir = "ALTA" if price_chg > 0.3 else "BAIXA" if price_chg < -0.3 else "LATERAL"

    # ── Aceleração de volume (últimos 3 vs média) ──────────────────────────
    recent_vol  = volume.iloc[-3:].mean() if len(volume) >= 3 else last_vol
    vol_accel   = recent_vol / avg_vol if avg_vol > 0 else 1.0

    # ── Score dimensional ──────────────────────────────────────────────────
    # Componente de direção: -50 a +50
    dir_score = 0.0
    if price_dir == "ALTA":
        dir_score = min(price_chg * 8, 50.0)
    elif price_dir == "BAIXA":
        dir_score = max(price_chg * 8, -50.0)

    # Componente de volume: 0 a 35 (amplifica a direção)
    vol_amp = min((vol_ratio - 1.0) * 15.0, 35.0) if vol_ratio > 1.0 else max((vol_ratio - 1.0) * 10.0, -20.0)

    # Componente de trades: 0 a 15
    trade_amp = min((trades_ratio - 1.0) * 10.0, 15.0) if trades_ratio > 1.0 else 0.0

    # Direção do sinal
    sign = 1.0 if price_dir != "BAIXA" else -1.0
    score = dir_score + sign * (abs(vol_amp) + abs(trade_amp))
    score = max(-100.0, min(100.0, score))

    # ── Pressão compradora/vendedora ───────────────────────────────────────
    buy_pressure  = max(0.0, score / 100.0)
    sell_pressure = max(0.0, -score / 100.0)

    # ── Classificação ──────────────────────────────────────────────────────
    if score >= 60:
        cls = "FORTE_COMPRA"
    elif score >= 25:
        cls = "COMPRA"
    elif score <= -60:
        cls = "FORTE_VENDA"
    elif score <= -25:
        cls = "VENDA"
    else:
        cls = "NEUTRO"

    # ── Texto explicativo ──────────────────────────────────────────────────
    _vol_txt = (
        f"Volume {vol_ratio:.1f}x acima da média"  if vol_ratio >= 1.3 else
        f"Volume normal ({vol_ratio:.1f}x)"         if vol_ratio >= 0.8 else
        f"Volume fraco ({vol_ratio:.1f}x da média)"
    )
    _dir_txt = (
        f"Preço em alta ({price_chg:+.1f}%)"     if price_dir == "ALTA" else
        f"Preço em queda ({price_chg:+.1f}%)"    if price_dir == "BAIXA" else
        "Preço lateral"
    )
    _trade_txt = (
        f", {trades_ratio:.1f}x mais negócios que a média."
        if trades_ratio >= 1.3 else "."
    )

    if cls == "FORTE_COMPRA":
        expl = f"Fluxo comprador consistente indicando continuidade do movimento. {_vol_txt}{_trade_txt} {_dir_txt}."
    elif cls == "COMPRA":
        expl = f"Pressão compradora moderada. {_vol_txt}. {_dir_txt}."
    elif cls == "FORTE_VENDA":
        expl = f"Agressão vendedora dominante. {_vol_txt}{_trade_txt} {_dir_txt}."
    elif cls == "VENDA":
        expl = f"Pressão vendedora moderada. {_vol_txt}. {_dir_txt}."
    else:
        expl = f"Fluxo equilibrado sem direcionalidade clara. {_vol_txt}. {_dir_txt}."

    return FlowResult(
        classification=cls,
        score=round(score, 1),
        intensity=round(abs(score) / 100.0, 3),
        buy_pressure=round(buy_pressure, 3),
        sell_pressure=round(sell_pressure, 3),
        volume_ratio=round(vol_ratio, 2),
        trades_ratio=round(trades_ratio, 2),
        price_direction=price_dir,
        explanation=expl,
    )


def compute_flow_from_db(asset: str, con, days: int = 30) -> FlowResult:
    """Carrega dados do DB e computa o flow."""
    import sqlite3
    try:
        query = """
            SELECT trade_date, close, volume, trades
            FROM cotahist_daily
            WHERE ticker = ? AND market_type = '010'
            ORDER BY trade_date DESC
            LIMIT ?
        """
        df = pd.read_sql(query, con, params=(asset, days))
        if df.empty:
            query2 = """
                SELECT trade_date, last AS close, volume, trades
                FROM profit_snapshots
                WHERE asset = ?
                ORDER BY captured_at DESC
                LIMIT ?
            """
            df = pd.read_sql(query2, con, params=(asset, days))
        df = df.sort_values("trade_date" if "trade_date" in df.columns else df.columns[0])
        return compute_flow(df)
    except Exception:
        return _neutral("Erro ao carregar dados.")


def flow_html(result: FlowResult) -> str:
    """Retorna o bloco HTML do fluxo para uso no dashboard."""
    label, color, dot = _CLS_MAP.get(result.classification, ("NEUTRO", "#64748B", "⬜"))
    intensity_pct = int(result.intensity * 100)
    bar_color = color

    buy_pct  = int(result.buy_pressure  * 100)
    sell_pct = int(result.sell_pressure * 100)

    return f"""
<div style="background:#0D1421;border:1px solid #1E2D42;border-radius:10px;padding:14px 16px;margin-top:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#334155">
      Fluxo de Mercado
    </span>
    <span style="font-size:0.8rem;font-weight:800;color:{color}">{dot} {label}</span>
  </div>

  <div style="font-size:0.78rem;color:#475569;line-height:1.6;margin-bottom:10px">
    {result.explanation}
  </div>

  <div style="display:flex;gap:12px;margin-bottom:8px">
    <div style="flex:1">
      <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px">Compra</div>
      <div style="background:#1E2D42;border-radius:3px;height:6px">
        <div style="width:{buy_pct}%;height:6px;border-radius:3px;background:#22C55E;transition:width 0.3s"></div>
      </div>
      <div style="font-size:0.7rem;color:#22C55E;margin-top:2px">{buy_pct}%</div>
    </div>
    <div style="flex:1">
      <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px">Venda</div>
      <div style="background:#1E2D42;border-radius:3px;height:6px">
        <div style="width:{sell_pct}%;height:6px;border-radius:3px;background:#EF4444;transition:width 0.3s"></div>
      </div>
      <div style="font-size:0.7rem;color:#EF4444;margin-top:2px">{sell_pct}%</div>
    </div>
    <div style="flex:1">
      <div style="font-size:0.6rem;color:#334155;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px">Intensidade</div>
      <div style="background:#1E2D42;border-radius:3px;height:6px">
        <div style="width:{intensity_pct}%;height:6px;border-radius:3px;background:{bar_color}"></div>
      </div>
      <div style="font-size:0.7rem;color:{color};margin-top:2px">{intensity_pct}%</div>
    </div>
  </div>

  <div style="display:flex;gap:16px;font-size:0.72rem;color:#334155">
    <span>Vol ratio: <strong style="color:#CBD5E1">{result.volume_ratio}x</strong></span>
    <span>Trades ratio: <strong style="color:#CBD5E1">{result.trades_ratio}x</strong></span>
    <span>Direção: <strong style="color:#CBD5E1">{result.price_direction}</strong></span>
    <span>Score: <strong style="color:{color}">{result.score:+.0f}</strong></span>
  </div>
</div>
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def avg_safe(s: pd.Series) -> bool:
    return len(s) > 0 and s.sum() > 0


def _neutral(msg: str) -> FlowResult:
    return FlowResult(
        classification="NEUTRO", score=0.0, intensity=0.0,
        buy_pressure=0.0, sell_pressure=0.0,
        volume_ratio=1.0, trades_ratio=1.0,
        price_direction="LATERAL", explanation=msg,
    )
