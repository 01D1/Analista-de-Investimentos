"""
Chart Engine — Gráficos profissionais estilo TradingView usando Plotly.

render_chart(asset, con, setup=None) → go.Figure
  - Candlestick OHLC + VWAP + EMA 9/21/200
  - Volume colorido
  - RSI (14)
  - MACD (12/26/9)
  - Marcadores de entrada / stop / alvo do setup
"""
from __future__ import annotations

from typing import Optional
import math

import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from src.quant.indicators import ema, rsi, macd, vwap as _vwap

# Paleta dark TradingView
_BG       = "#080D17"
_BG2      = "#111827"
_GRID     = "#1E2D42"
_TEXT     = "#64748B"
_GREEN    = "#22C55E"
_RED      = "#EF4444"
_BLUE     = "#3B82F6"
_PURPLE   = "#7C3AED"
_AMBER    = "#F59E0B"
_CYAN     = "#06B6D4"
_WHITE    = "#E2E8F0"


def load_ohlcv(asset: str, con, days: int = 252) -> pd.DataFrame:
    """Carrega OHLCV do cotahist_daily (ações à vista, market_type='010')."""
    query = """
        SELECT trade_date, open, high, low, close, volume, trades
        FROM cotahist_daily
        WHERE ticker = ? AND market_type = '010'
        ORDER BY trade_date DESC
        LIMIT ?
    """
    df = pd.read_sql(query, con, params=(asset, days))
    if df.empty:
        # Fallback: b3_quotes
        query2 = """
            SELECT trade_date, open, high, low, close, volume
            FROM b3_quotes
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT ?
        """
        df = pd.read_sql(query2, con, params=(asset, days))
        df["trades"] = 0

    if df.empty:
        return df

    df = df.sort_values("trade_date").reset_index(drop=True)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    # Garante float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"])
    return df


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close  = df["close"]
    volume = df["volume"]
    high   = df["high"]
    low    = df["low"]

    df = df.copy()
    df["ema9"]   = ema(close, 9)
    df["ema21"]  = ema(close, 21)
    df["ema200"] = ema(close, 200)

    # VWAP rolling 20d (proxy para swing trading)
    typical = (high + low + close) / 3
    roll_vol = volume.rolling(20, min_periods=1)
    roll_pv  = (typical * volume).rolling(20, min_periods=1)
    df["vwap"] = roll_pv.sum() / roll_vol.sum().replace(0, np.nan)

    df["rsi14"] = rsi(close, 14)

    ml, sl, hist = macd(close, 12, 26, 9)
    df["macd_line"]   = ml
    df["macd_signal"] = sl
    df["macd_hist"]   = hist

    # Cores do candle e do volume
    df["candle_color"] = df.apply(
        lambda r: _GREEN if r["close"] >= r["open"] else _RED, axis=1
    )
    return df


def _dark_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=_BG,
        plot_bgcolor=_BG2,
        font=dict(family="Inter, sans-serif", size=11, color=_TEXT),
        title=dict(
            text=title, font=dict(size=14, color=_WHITE, weight="bold"), x=0.01
        ),
        legend=dict(
            bgcolor=_BG2, bordercolor=_GRID, borderwidth=1,
            font=dict(size=10, color=_TEXT),
            x=0.01, y=0.98,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=_BG2, bordercolor=_GRID, font_color=_WHITE),
        xaxis_rangeslider_visible=False,
    )
    # Estilo dos eixos
    axis_style = dict(
        showgrid=True, gridcolor=_GRID, gridwidth=1,
        zeroline=False,
        showline=True, linecolor=_GRID,
        tickfont=dict(color=_TEXT, size=10),
    )
    for ax in ["xaxis", "xaxis2", "xaxis3", "xaxis4",
               "yaxis", "yaxis2", "yaxis3", "yaxis4"]:
        fig.update_layout(**{ax: axis_style})
    return fig


def render_chart(
    asset: str,
    con,
    setup=None,
    days: int = 252,
) -> Optional["go.Figure"]:
    """
    Cria o gráfico profissional completo para o ativo.

    Args:
        asset:  ticker do ativo (ex. 'PETR4')
        con:    conexão sqlite3
        setup:  StrategyOpportunity (opcional) — adiciona marcadores entry/stop/alvo
        days:   número de pregões históricos

    Returns:
        Figura Plotly ou None se plotly não instalado / sem dados.
    """
    if not HAS_PLOTLY:
        return None

    df = load_ohlcv(asset, con, days)
    if df.empty:
        return None

    df = _add_indicators(df)
    dates = df["trade_date"]

    # ── Layout em 4 linhas ──────────────────────────────────────────────────
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=["", "Volume", "RSI (14)", "MACD (12/26/9)"],
    )

    # ── ROW 1: Candlestick ─────────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=dates, open=df["open"], high=df["high"],
            low=df["low"],  close=df["close"],
            increasing_line_color=_GREEN, decreasing_line_color=_RED,
            increasing_fillcolor=_GREEN, decreasing_fillcolor=_RED,
            name=asset, showlegend=True,
            line_width=1,
        ),
        row=1, col=1,
    )

    # EMA 9
    fig.add_trace(
        go.Scatter(x=dates, y=df["ema9"], name="EMA 9",
                   line=dict(color="#F59E0B", width=1.2, dash="solid"),
                   opacity=0.85),
        row=1, col=1,
    )
    # EMA 21
    fig.add_trace(
        go.Scatter(x=dates, y=df["ema21"], name="EMA 21",
                   line=dict(color=_BLUE, width=1.4),
                   opacity=0.85),
        row=1, col=1,
    )
    # EMA 200
    fig.add_trace(
        go.Scatter(x=dates, y=df["ema200"], name="EMA 200",
                   line=dict(color=_PURPLE, width=1.6),
                   opacity=0.80),
        row=1, col=1,
    )
    # VWAP
    fig.add_trace(
        go.Scatter(x=dates, y=df["vwap"], name="VWAP",
                   line=dict(color=_CYAN, width=1.3, dash="dot"),
                   opacity=0.90),
        row=1, col=1,
    )

    # ── Marcadores do setup ────────────────────────────────────────────────
    if setup is not None:
        p = setup.payoff
        spot = p.stock_price
        last_date = dates.iloc[-1]

        # Entrada = spot atual
        fig.add_hline(
            y=spot, line_color=_AMBER, line_width=1.5, line_dash="dash",
            annotation_text=f"  Entrada R${spot:.2f}",
            annotation_font_color=_AMBER,
            row=1, col=1,
        )

        # Breakevens / alvos
        for i, be in enumerate(p.breakevens[:2]):
            fig.add_hline(
                y=be, line_color=_GREEN, line_width=1.2, line_dash="dot",
                annotation_text=f"  BE R${be:.2f}",
                annotation_font_color=_GREEN,
                row=1, col=1,
            )

        # Stop (se risco definido)
        if not math.isinf(p.max_loss) and p.max_loss > 0:
            # Aproxima o stop pelo breakeven mínimo ou spot - max_loss
            stop_price = min(p.breakevens) if p.breakevens else spot * 0.95
            fig.add_hline(
                y=stop_price, line_color=_RED, line_width=1.2, line_dash="longdash",
                annotation_text=f"  Stop R${stop_price:.2f}",
                annotation_font_color=_RED,
                row=1, col=1,
            )

        # Alvo
        if not math.isinf(p.max_profit):
            target_price = max(p.breakevens) if len(p.breakevens) > 1 else spot * 1.10
            fig.add_hline(
                y=target_price, line_color=_GREEN, line_width=1.5, line_dash="longdash",
                annotation_text=f"  Alvo R${target_price:.2f}",
                annotation_font_color=_GREEN,
                row=1, col=1,
            )

    # ── ROW 2: Volume ──────────────────────────────────────────────────────
    fig.add_trace(
        go.Bar(
            x=dates, y=df["volume"],
            marker_color=df["candle_color"],
            marker_line_width=0,
            name="Volume", opacity=0.7,
            showlegend=False,
        ),
        row=2, col=1,
    )

    # ── ROW 3: RSI ─────────────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(x=dates, y=df["rsi14"], name="RSI(14)",
                   line=dict(color=_PURPLE, width=1.5),
                   showlegend=False),
        row=3, col=1,
    )
    # Zonas RSI
    fig.add_hrect(y0=70, y1=100, line_width=0,
                  fillcolor=_RED, opacity=0.06, row=3, col=1)
    fig.add_hrect(y0=0, y1=30, line_width=0,
                  fillcolor=_GREEN, opacity=0.06, row=3, col=1)
    fig.add_hline(y=70, line_color=_RED,   line_width=0.8, line_dash="dot", row=3, col=1)
    fig.add_hline(y=30, line_color=_GREEN, line_width=0.8, line_dash="dot", row=3, col=1)
    fig.add_hline(y=50, line_color=_GRID,  line_width=0.8, line_dash="dot", row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    # ── ROW 4: MACD ────────────────────────────────────────────────────────
    hist_colors = [_GREEN if v >= 0 else _RED for v in df["macd_hist"].fillna(0)]
    fig.add_trace(
        go.Bar(x=dates, y=df["macd_hist"],
               marker_color=hist_colors, marker_line_width=0,
               name="MACD Hist", opacity=0.75, showlegend=False),
        row=4, col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=df["macd_line"], name="MACD",
                   line=dict(color=_BLUE, width=1.4), showlegend=False),
        row=4, col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=df["macd_signal"], name="Signal",
                   line=dict(color=_AMBER, width=1.2, dash="dot"), showlegend=False),
        row=4, col=1,
    )
    fig.add_hline(y=0, line_color=_GRID, line_width=0.8, row=4, col=1)

    # ── Estilo final ───────────────────────────────────────────────────────
    setup_name = f" · {setup.name}" if setup else ""
    fig = _dark_layout(fig, f"{asset}{setup_name}")

    fig.update_layout(
        height=700,
        xaxis_rangeslider_visible=False,
    )
    # Esconde títulos dos subplots (deixa eixo y rotulado)
    fig.update_annotations(font_size=10, font_color=_TEXT)

    return fig
