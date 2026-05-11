"""
Options Volatility Analysis — IV rank, IV smile, vol cone, term structure, Greeks table.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from src.quant.volatility import historical_volatility, volatility_cone, vol_term_structure

_BG     = "#080D17"
_BG2    = "#111827"
_GRID   = "#1E2D42"
_TEXT   = "#64748B"
_GREEN  = "#22C55E"
_RED    = "#EF4444"
_BLUE   = "#3B82F6"
_PURPLE = "#7C3AED"
_AMBER  = "#F59E0B"
_CYAN   = "#06B6D4"
_WHITE  = "#E2E8F0"

_LAYOUT_BASE = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG2,
    font=dict(family="Inter, sans-serif", size=11, color=_TEXT),
    legend=dict(bgcolor=_BG2, bordercolor=_GRID, borderwidth=1, font=dict(size=10, color=_TEXT)),
    margin=dict(l=0, r=0, t=44, b=0),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=_BG2, bordercolor=_GRID, font_color=_WHITE),
)

_AXIS_BASE = dict(showgrid=True, gridcolor=_GRID, zeroline=False, tickfont=dict(color=_TEXT, size=10))


# ── IV Rank & Percentile ──────────────────────────────────────────────────────

def iv_rank(current_iv: float, iv_series: pd.Series) -> float:
    """(IV_atual − IV_min) / (IV_max − IV_min) × 100."""
    s = iv_series.dropna()
    if len(s) < 5:
        return float("nan")
    lo, hi = float(s.min()), float(s.max())
    if hi - lo < 1e-6:
        return 50.0
    return round((current_iv - lo) / (hi - lo) * 100, 1)


def iv_percentile(current_iv: float, iv_series: pd.Series) -> float:
    """% das observações históricas abaixo do IV atual."""
    s = iv_series.dropna()
    if len(s) < 5:
        return float("nan")
    return round(float((s < current_iv).sum()) / len(s) * 100, 1)


# ── IV Stats consolidados ─────────────────────────────────────────────────────

def compute_iv_stats(chain, prices: pd.DataFrame) -> dict:
    """
    Retorna:
        iv_atm, hv_21, iv_hv_spread, iv_rank, iv_percentile,
        skew_25d, iv_call_25d, iv_put_25d
    """
    all_recs = [r for r in list(chain.calls) + list(chain.puts) if not math.isnan(r.iv_implied)]

    # IV ATM: menor |moneyness_pct| com iv válida
    atm_recs = [r for r in all_recs if r.moneyness == "ATM"]
    if not atm_recs:
        atm_recs = sorted(all_recs, key=lambda r: abs(r.moneyness_pct))[:4]

    iv_atm = float(np.mean([r.iv_implied for r in atm_recs])) if atm_recs else chain.hv
    hv_21  = chain.hv
    iv_hv  = iv_atm - hv_21

    # IV rank / percentile usando série de HV como proxy
    ivr = ivp = float("nan")
    if prices is not None and not prices.empty and len(prices) >= 30:
        hv_series = historical_volatility(prices["close"], window=21)
        ivr = iv_rank(iv_atm, hv_series)
        ivp = iv_percentile(iv_atm, hv_series)

    # 25-delta skew
    c25 = [r for r in chain.calls if 0.20 <= abs(r.delta) <= 0.30 and not math.isnan(r.iv_implied)]
    p25 = [r for r in chain.puts  if 0.20 <= abs(r.delta) <= 0.30 and not math.isnan(r.iv_implied)]
    iv_c25 = float(np.mean([r.iv_implied for r in c25])) if c25 else float("nan")
    iv_p25 = float(np.mean([r.iv_implied for r in p25])) if p25 else float("nan")
    skew   = iv_p25 - iv_c25 if (not math.isnan(iv_p25) and not math.isnan(iv_c25)) else float("nan")

    return {
        "iv_atm": iv_atm,
        "hv_21": hv_21,
        "iv_hv_spread": iv_hv,
        "iv_rank": ivr,
        "iv_percentile": ivp,
        "skew_25d": skew,
        "iv_call_25d": iv_c25,
        "iv_put_25d": iv_p25,
    }


# ── IV Smile ──────────────────────────────────────────────────────────────────

def build_iv_smile_chart(chain, expiry: str | None = None) -> "go.Figure | None":
    """IV implícita vs moneyness% para calls e puts de um vencimento."""
    if not HAS_PLOTLY:
        return None

    valid = [r for r in list(chain.calls) + list(chain.puts)
             if not math.isnan(r.iv_implied) and r.liq_score >= 10]
    if not valid:
        return None

    if expiry is None:
        from collections import Counter
        expiry = Counter(r.expiry for r in valid).most_common(1)[0][0]

    calls = sorted([r for r in chain.calls if r.expiry == expiry
                    and not math.isnan(r.iv_implied) and r.liq_score >= 10],
                   key=lambda r: r.strike)
    puts  = sorted([r for r in chain.puts  if r.expiry == expiry
                    and not math.isnan(r.iv_implied) and r.liq_score >= 10],
                   key=lambda r: r.strike)

    if not calls and not puts:
        return None

    fig = go.Figure()

    if calls:
        fig.add_trace(go.Scatter(
            x=[r.moneyness_pct for r in calls],
            y=[r.iv_implied * 100 for r in calls],
            mode="lines+markers", name="CALL",
            line=dict(color=_BLUE, width=2.2),
            marker=dict(size=7, color=_BLUE),
            customdata=[[r.ticker, r.strike, r.delta, r.liq_score, r.theta] for r in calls],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Strike R$%{customdata[1]:.2f}<br>"
                "IV %{y:.1f}%<br>"
                "Delta %{customdata[2]:.3f}<br>"
                "Theta %{customdata[4]:.4f}/d<br>"
                "Liq %{customdata[3]:.0f}"
                "<extra>CALL</extra>"
            ),
        ))

    if puts:
        fig.add_trace(go.Scatter(
            x=[r.moneyness_pct for r in puts],
            y=[r.iv_implied * 100 for r in puts],
            mode="lines+markers", name="PUT",
            line=dict(color=_PURPLE, width=2.2),
            marker=dict(size=7, color=_PURPLE),
            customdata=[[r.ticker, r.strike, r.delta, r.liq_score, r.theta] for r in puts],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Strike R$%{customdata[1]:.2f}<br>"
                "IV %{y:.1f}%<br>"
                "Delta %{customdata[2]:.3f}<br>"
                "Theta %{customdata[4]:.4f}/d<br>"
                "Liq %{customdata[3]:.0f}"
                "<extra>PUT</extra>"
            ),
        ))

    # HV de referência
    hv_line = chain.hv * 100
    fig.add_hline(
        y=hv_line, line_color=_GREEN, line_width=1.4, line_dash="dot",
        annotation_text=f"  HV21 {hv_line:.1f}%",
        annotation_font_color=_GREEN, annotation_font_size=10,
    )
    # ATM
    fig.add_vline(x=0, line_color=_AMBER, line_width=1.2, line_dash="dot",
                  annotation_text="ATM", annotation_font_color=_AMBER, annotation_font_size=10)

    dte = next((r.dte for r in (calls or puts)), "?")
    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=f"IV Smile — Vto {expiry} · DTE {dte}d", font=dict(size=13, color=_WHITE), x=0.01),
        xaxis=dict(**_AXIS_BASE, title="Moneyness (%)", ticksuffix="%"),
        yaxis=dict(**_AXIS_BASE, title="IV Implícita (%)", ticksuffix="%"),
        height=360,
    )
    return fig


# ── Volatility Cone ───────────────────────────────────────────────────────────

def build_vol_cone_chart(prices: pd.DataFrame, chain=None) -> "go.Figure | None":
    """Cone de volatilidade histórica + IV ATM atual."""
    if not HAS_PLOTLY or prices is None or prices.empty or len(prices) < 63:
        return None

    cone = volatility_cone(prices["close"])
    if cone.empty:
        return None

    windows = cone.index.tolist()

    fig = go.Figure()

    # Faixas do cone
    fig.add_trace(go.Scatter(
        x=windows + windows[::-1],
        y=(cone["p90"] * 100).tolist() + (cone["p10"] * 100).tolist()[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.07)",
        line=dict(color="rgba(0,0,0,0)"), name="P10–P90", showlegend=True,
    ))
    fig.add_trace(go.Scatter(
        x=windows + windows[::-1],
        y=(cone["p75"] * 100).tolist() + (cone["p25"] * 100).tolist()[::-1],
        fill="toself", fillcolor="rgba(59,130,246,0.18)",
        line=dict(color="rgba(0,0,0,0)"), name="P25–P75", showlegend=True,
    ))

    # Mediana e HV atual
    fig.add_trace(go.Scatter(
        x=windows, y=cone["p50"] * 100, mode="lines", name="Mediana",
        line=dict(color=_BLUE, width=1.8, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=windows, y=cone["current"] * 100, mode="lines+markers", name="HV Atual",
        line=dict(color=_GREEN, width=2.5),
        marker=dict(size=9, color=_GREEN, symbol="diamond"),
        hovertemplate="Janela %{x}d<br>HV atual %{y:.1f}%<extra></extra>",
    ))

    # IV ATM
    if chain is not None:
        atm_ivs = [r.iv_implied for r in list(chain.calls) + list(chain.puts)
                   if r.moneyness == "ATM" and not math.isnan(r.iv_implied)]
        if atm_ivs:
            iv_atm_pct = float(np.mean(atm_ivs)) * 100
            fig.add_hline(
                y=iv_atm_pct, line_color=_AMBER, line_width=2,
                annotation_text=f"  IV ATM {iv_atm_pct:.1f}%",
                annotation_font_color=_AMBER, annotation_font_size=11,
            )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Volatility Cone — HV histórica vs IV ATM atual", font=dict(size=13, color=_WHITE), x=0.01),
        xaxis=dict(**_AXIS_BASE, title="Janela (pregões)", tickvals=windows),
        yaxis=dict(**_AXIS_BASE, title="Vol Anualizada (%)", ticksuffix="%"),
        height=360,
    )
    return fig


# ── Term Structure ────────────────────────────────────────────────────────────

def build_term_structure_chart(chain) -> "go.Figure | None":
    """IV ATM por DTE para calls e puts (estrutura a termo)."""
    if not HAS_PLOTLY:
        return None

    ts_c = vol_term_structure(
        [r for r in chain.calls if not math.isnan(r.iv_implied)], opt_type="CALL"
    )
    ts_p = vol_term_structure(
        [r for r in chain.puts if not math.isnan(r.iv_implied)], opt_type="PUT"
    )

    if ts_c.empty and ts_p.empty:
        return None

    fig = go.Figure()

    if not ts_c.empty:
        fig.add_trace(go.Scatter(
            x=ts_c["dte"], y=ts_c["iv_atm"] * 100,
            mode="lines+markers", name="CALL ATM",
            line=dict(color=_BLUE, width=2.2),
            marker=dict(size=9, color=_BLUE),
            hovertemplate="DTE %{x}d · IV %{y:.1f}%<extra>CALL</extra>",
        ))

    if not ts_p.empty:
        fig.add_trace(go.Scatter(
            x=ts_p["dte"], y=ts_p["iv_atm"] * 100,
            mode="lines+markers", name="PUT ATM",
            line=dict(color=_PURPLE, width=2.2),
            marker=dict(size=9, color=_PURPLE),
            hovertemplate="DTE %{x}d · IV %{y:.1f}%<extra>PUT</extra>",
        ))

    # HV de referência
    hv_line = chain.hv * 100
    fig.add_hline(
        y=hv_line, line_color=_GREEN, line_width=1.4, line_dash="dot",
        annotation_text=f"  HV21 {hv_line:.1f}%",
        annotation_font_color=_GREEN, annotation_font_size=10,
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Estrutura a Termo da IV (ATM por DTE)", font=dict(size=13, color=_WHITE), x=0.01),
        xaxis=dict(**_AXIS_BASE, title="Dias até Vencimento (DTE)"),
        yaxis=dict(**_AXIS_BASE, title="IV ATM (%)", ticksuffix="%"),
        hovermode="x",
        height=320,
    )
    return fig


# ── Greeks Table ──────────────────────────────────────────────────────────────

def build_greeks_table(chain) -> pd.DataFrame:
    """DataFrame com Greeks completos da cadeia, filtrado por liquidez mínima."""
    rows = []
    for r in sorted(
        list(chain.calls) + list(chain.puts),
        key=lambda x: (x.expiry, x.option_type, x.strike),
    ):
        if math.isnan(r.iv_implied) or r.liq_score < 10:
            continue
        rows.append({
            "Ticker":   r.ticker,
            "Tipo":     r.option_type,
            "Strike":   r.strike,
            "Vto":      r.expiry,
            "DTE":      r.dte,
            "Preço":    r.price,
            "IV (%)":   round(r.iv_implied * 100, 1),
            "HV (%)":   round(r.iv_hv * 100, 1),
            "Δ IV-HV":  round((r.iv_implied - r.iv_hv) * 100, 1),
            "Delta":    round(r.delta, 3),
            "Gamma":    round(r.gamma, 5),
            "Theta/d":  round(r.theta, 4),
            "Vega/1%":  round(r.vega, 4),
            "Vanna":    round(r.vanna, 4),
            "Charm":    round(r.charm, 5),
            "Moneyness": r.moneyness,
            "Liq":      int(r.liq_score),
        })
    return pd.DataFrame(rows)
