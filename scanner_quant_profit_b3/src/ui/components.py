"""
Premium reusable UI components for Plataforma Quant B3.

All functions either return an HTML string or call st.markdown directly.
No function modifies data — strictly visual layer.
"""
from __future__ import annotations

import json
import html as _html
from typing import Any

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore[assignment]

try:
    import plotly.graph_objects as go
except ImportError:
    go = None  # type: ignore[assignment]


# ── Positioning maps ──────────────────────────────────────────────────────────

_POSITIONING_BADGE = {
    "COMPRAR": ("BUY",  "badge-buy"),
    "MANTER":  ("HOLD", "badge-hold"),
    "VENDER":  ("SELL", "badge-sell"),
}

_POSITIONING_CLASS = {
    "COMPRAR": "buy",
    "MANTER":  "hold",
    "VENDER":  "sell",
}

_IMPACT_BADGE = {
    "HIGH":   "badge-high",
    "MEDIUM": "badge-medium",
    "LOW":    "badge-low",
    "ALTA":   "badge-high",
    "MEDIA":  "badge-medium",
    "BAIXA":  "badge-low",
}

_SIGNAL_CLASS = {
    "DCF_DIVERGENCE":     "dcf",
    "MOMENTUM_CROSSOVER": "momentum",
    "IPE_EVENT":          "ipe",
}


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _esc(text: Any) -> str:
    """HTML-escape a value safely."""
    return _html.escape(str(text) if text is not None else "—")


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


# ═════════════════════════════════════════════════════════════════════════════
# BADGE
# ═════════════════════════════════════════════════════════════════════════════

def badge(text: str, style: str = "neutral") -> str:
    """Return an inline HTML badge span."""
    css_class = "badge badge-{0}".format(style)
    return '<span class="{0}">{1}</span>'.format(css_class, _esc(text))


def positioning_badge(positioning: str) -> str:
    """BUY/HOLD/SELL badge with appropriate color class."""
    label, css = _POSITIONING_BADGE.get(
        positioning.upper(), (positioning, "badge-neutral")
    )
    return '<span class="badge {0}">{1}</span>'.format(css, label)


def impact_badge(level: str) -> str:
    """HIGH/MEDIUM/LOW impact badge."""
    css = _IMPACT_BADGE.get(level.upper(), "badge-neutral")
    return '<span class="badge {0}">{1}</span>'.format(css, _esc(level))


# ═════════════════════════════════════════════════════════════════════════════
# SECTION TITLE
# ═════════════════════════════════════════════════════════════════════════════

def section_title(text: str, icon: str = "") -> None:
    """Render a section divider with title using st.markdown."""
    icon_html = (
        '<span class="section-title-icon">{0}</span>'.format(_esc(icon))
        if icon else ""
    )
    st.markdown(
        '<div class="section-title">{0}{1}</div>'.format(icon_html, _esc(text)),
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# EMPTY STATE
# ═════════════════════════════════════════════════════════════════════════════

def empty_state(message: str, icon: str = "") -> None:
    """Render a centered empty state placeholder."""
    st.markdown(
        """
<div class="empty-state">
  <div class="empty-state-icon">{icon}</div>
  <div class="empty-state-text">{msg}</div>
</div>""".format(icon=_esc(icon), msg=_esc(message)),
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# KPI CARD / STRIP
# ═════════════════════════════════════════════════════════════════════════════

def kpi_card(
    label: str,
    value: str,
    sub: str = "",
    color: str = "blue",
    delta: float | None = None,
) -> str:
    """Return HTML for a single KPI card."""
    delta_html = ""
    if delta is not None:
        if delta >= 0:
            delta_html = '<div class="kpi-delta-pos">&#9650; {0:+.1f}%</div>'.format(delta)
        else:
            delta_html = '<div class="kpi-delta-neg">&#9660; {0:.1f}%</div>'.format(delta)

    sub_html = (
        '<div class="kpi-sub">{0}</div>'.format(_esc(sub)) if sub else ""
    )

    return """
<div class="kpi-card {color}">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  {sub}
  {delta}
</div>""".format(
        color=_esc(color),
        label=_esc(label),
        value=_esc(value),
        sub=sub_html,
        delta=delta_html,
    )


def kpi_strip(cards: list[dict]) -> None:
    """Render a horizontal row of KPI cards.

    Each card dict: {label, value, sub?, color?, delta?}
    """
    inner = "".join(
        kpi_card(
            label=c.get("label", ""),
            value=c.get("value", "—"),
            sub=c.get("sub", ""),
            color=c.get("color", "blue"),
            delta=c.get("delta"),
        )
        for c in cards
    )
    st.markdown(
        '<div class="kpi-strip">{0}</div>'.format(inner),
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ═════════════════════════════════════════════════════════════════════════════

def hero_section(
    ticker: str,
    nome: str = "",
    setor: str = "",
    positioning: str = "",
    score: float = 0.0,
    market_cap: str | None = None,
    upside: float | None = None,
) -> None:
    """Render a hero banner for the asset detail page."""
    pos_badge = positioning_badge(positioning) if positioning else ""
    setor_badge = (
        '<span class="badge badge-neutral" style="margin-left:8px">{0}</span>'.format(_esc(setor))
        if setor else ""
    )

    upside_html = ""
    if upside is not None:
        color = "#22C55E" if upside >= 0 else "#EF4444"
        sign = "+" if upside >= 0 else ""
        upside_html = """
    <div class="hero-metric">
      Upside DCF
      <span style="color:{color}">{sign}{upside:.1f}%</span>
    </div>""".format(color=color, sign=sign, upside=upside)

    mktcap_html = ""
    if market_cap:
        mktcap_html = """
    <div class="hero-metric">
      Market Cap
      <span>{0}</span>
    </div>""".format(_esc(market_cap))

    score_pct = _clamp(score)
    st.markdown(
        """
<div class="hero-section">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <div class="hero-ticker">{ticker}</div>
      <div class="hero-company">{nome}{setor_badge}</div>
      <div style="margin-top:10px">{pos_badge}</div>
    </div>
    <div style="text-align:right;font-size:3rem;font-weight:900;color:#1E2D42;
                line-height:1;user-select:none;letter-spacing:-2px">{score_display}</div>
  </div>
  <div class="hero-meta">
    {upside_html}
    {mktcap_html}
  </div>
</div>""".format(
            ticker=_esc(ticker),
            nome=_esc(nome) if nome else _esc(ticker),
            setor_badge=setor_badge,
            pos_badge=pos_badge,
            score_display="{0:.0f}".format(score_pct),
            upside_html=upside_html,
            mktcap_html=mktcap_html,
        ),
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# SCORE GAUGE (Plotly)
# ═════════════════════════════════════════════════════════════════════════════

def score_gauge(score: float, label: str = "Score Geral") -> "go.Figure":
    """Return a Plotly Indicator gauge figure."""
    val = _clamp(score)

    if val >= 70:
        bar_color = "#22C55E"
    elif val >= 40:
        bar_color = "#F59E0B"
    else:
        bar_color = "#EF4444"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": label, "font": {"size": 13, "color": "#94A3B8"}},
            number={"font": {"size": 36, "color": "#F1F5F9"}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": "#1E2D42",
                    "tickfont": {"size": 9, "color": "#475569"},
                },
                "bar": {"color": bar_color, "thickness": 0.22},
                "bgcolor": "#111827",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40],  "color": "rgba(239,68,68,0.08)"},
                    {"range": [40, 70], "color": "rgba(245,158,11,0.08)"},
                    {"range": [70, 100],"color": "rgba(34,197,94,0.08)"},
                ],
                "threshold": {
                    "line": {"color": "#3B82F6", "width": 2},
                    "thickness": 0.8,
                    "value": val,
                },
            },
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94A3B8"},
        margin={"l": 20, "r": 20, "t": 30, "b": 10},
        height=220,
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# SCORE BREAKDOWN BARS
# ═════════════════════════════════════════════════════════════════════════════

_BAR_COLORS = ["blue", "green", "amber", "purple", "red", "blue"]


def score_breakdown_bars(dimensions: dict[str, float]) -> None:
    """Render animated horizontal score bars via HTML."""
    rows_html = []
    for idx, (dim_name, raw_val) in enumerate(dimensions.items()):
        val = _clamp(raw_val)
        color_class = "score-bar-{0}".format(
            _BAR_COLORS[idx % len(_BAR_COLORS)]
        )
        rows_html.append(
            """
<div class="score-bar-row">
  <div class="score-bar-label">
    <span>{name}</span>
    <span>{val:.0f}</span>
  </div>
  <div class="score-bar-track">
    <div class="score-bar-fill {color}" style="width:{val:.1f}%"></div>
  </div>
</div>""".format(
                name=_esc(dim_name),
                val=val,
                color=color_class,
            )
        )
    st.markdown("".join(rows_html), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# THESIS CARD
# ═════════════════════════════════════════════════════════════════════════════

def thesis_card(
    bull_case: str,
    bear_case: str,
    drivers: list[dict],
    risks: list[dict],
) -> None:
    """Render bull/bear case text in a styled thesis card."""
    st.markdown(
        """
<div class="thesis-card">
  <div class="thesis-section-title bull">Cenario Otimista (Bull Case)</div>
  <div class="thesis-text">{bull}</div>
  <hr class="thesis-divider">
  <div class="thesis-section-title bear">Cenario Pessimista (Bear Case)</div>
  <div class="thesis-text">{bear}</div>
</div>""".format(
            bull=_esc(bull_case or "—"),
            bear=_esc(bear_case or "—"),
        ),
        unsafe_allow_html=True,
    )


def driver_list(drivers: list[dict]) -> None:
    """Render a list of investment drivers."""
    if not drivers:
        st.caption("Nenhum driver disponivel.")
        return
    items = []
    for d in drivers:
        imp = impact_badge(d.get("impact", "MEDIUM"))
        items.append(
            """
<div class="driver-item">
  <div class="driver-title">{title} {badge}</div>
  <div class="driver-desc">{desc}</div>
</div>""".format(
                title=_esc(d.get("title", "—")),
                badge=imp,
                desc=_esc(d.get("description", "")),
            )
        )
    st.markdown("".join(items), unsafe_allow_html=True)


def risk_list(risks: list[dict]) -> None:
    """Render a list of risks."""
    if not risks:
        st.caption("Nenhum risco disponivel.")
        return
    items = []
    for r in risks:
        sev = impact_badge(r.get("severity", "MEDIUM"))
        items.append(
            """
<div class="risk-item">
  <div class="risk-title">{title} {badge}</div>
  <div class="risk-desc">{desc}</div>
</div>""".format(
                title=_esc(r.get("title", "—")),
                badge=sev,
                desc=_esc(r.get("description", "")),
            )
        )
    st.markdown("".join(items), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# RADAR CHART (Plotly)
# ═════════════════════════════════════════════════════════════════════════════

def radar_chart(dimensions: dict[str, float], ticker: str = "") -> "go.Figure":
    """Return a Plotly polar/radar chart."""
    cats = list(dimensions.keys())
    vals = [_clamp(v) for v in dimensions.values()]
    # close the polygon
    cats_closed = cats + [cats[0]]
    vals_closed  = vals + [vals[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=vals_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor="rgba(59,130,246,0.12)",
            line={"color": "#3B82F6", "width": 2},
            name=ticker or "Score",
            hovertemplate="%{theta}: %{r:.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        polar={
            "bgcolor": "rgba(17,24,39,1)",
            "radialaxis": {
                "range": [0, 100],
                "tickfont": {"size": 8, "color": "#475569"},
                "gridcolor": "#1E2D42",
                "linecolor": "#1E2D42",
            },
            "angularaxis": {
                "tickfont": {"size": 10, "color": "#94A3B8"},
                "gridcolor": "#1E2D42",
                "linecolor": "#1E2D42",
            },
        },
        font={"color": "#94A3B8"},
        margin={"l": 30, "r": 30, "t": 30, "b": 30},
        height=300,
        showlegend=False,
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# SPARKLINE CARD (Plotly mini)
# ═════════════════════════════════════════════════════════════════════════════

def sparkline_card(
    label: str,
    values: list[float],
    current: float,
    delta: float | None = None,
) -> "go.Figure":
    """Return a small Plotly line figure for a sparkline card."""
    color = "#22C55E" if (delta or 0) >= 0 else "#EF4444"
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            y=values,
            mode="lines",
            line={"color": color, "width": 1.5},
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.08)").replace("rgb(", "rgba("),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,1)",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        height=60,
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# WATCHLIST ROW / CARD
# ═════════════════════════════════════════════════════════════════════════════

def watchlist_card(row: dict) -> str:
    """Return HTML for one watchlist asset card."""
    ticker = _esc(row.get("ticker", "—"))
    positioning = str(row.get("positioning", "MANTER")).upper()
    pos_class = _POSITIONING_CLASS.get(positioning, "hold")
    pos_bdg = positioning_badge(positioning)

    fair_val = row.get("fair_value_brl")
    fair_str = "R$ {0:.2f}".format(fair_val) if fair_val else "—"

    upside = row.get("upside_pct")
    if upside is not None:
        try:
            upside_f = float(upside)
            upside_color = "#22C55E" if upside_f >= 0 else "#EF4444"
            upside_str = '{0:+.1f}%'.format(upside_f)
        except (TypeError, ValueError):
            upside_color = "#94A3B8"
            upside_str = "—"
    else:
        upside_color = "#94A3B8"
        upside_str = "—"

    price = row.get("price")
    price_str = "R$ {0:.2f}".format(price) if price else "—"

    confidence = _esc(row.get("confidence", "—"))
    generated_at = _esc(str(row.get("generated_at", ""))[:10] or "—")

    return """
<div class="watchlist-row {pos_class}">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <div class="watchlist-ticker">{ticker}</div>
    {pos_bdg}
  </div>
  <div class="watchlist-details">
    <div class="watchlist-detail-item">Valor Justo<span>{fair}</span></div>
    <div class="watchlist-detail-item">Upside<span style="color:{up_color}">{upside}</span></div>
    <div class="watchlist-detail-item">Preco<span>{price}</span></div>
    <div class="watchlist-detail-item">Confianca<span>{conf}</span></div>
  </div>
  <div style="margin-top:8px;font-size:0.62rem;color:#475569">Atualizado: {gen}</div>
</div>""".format(
        pos_class=pos_class,
        ticker=ticker,
        pos_bdg=pos_bdg,
        fair=fair_str,
        up_color=upside_color,
        upside=upside_str,
        price=price_str,
        conf=confidence,
        gen=generated_at,
    )


# ═════════════════════════════════════════════════════════════════════════════
# OPPORTUNITY CARD
# ═════════════════════════════════════════════════════════════════════════════

def opportunity_card(
    ticker: str,
    description: str,
    signal_type: str,
    conviction_score: int,
) -> str:
    """Return HTML for one opportunity card."""
    sig_upper = signal_type.upper()
    if "DCF" in sig_upper:
        sig_class = "dcf"
        sig_label = "DCF Divergence"
    elif "MOMENTUM" in sig_upper:
        sig_class = "momentum"
        sig_label = "Momentum"
    elif "IPE" in sig_upper or "EVENT" in sig_upper:
        sig_class = "ipe"
        sig_label = "IPE Event"
    else:
        sig_class = "default"
        sig_label = signal_type[:22]

    score_val = _clamp(float(conviction_score or 0))

    return """
<div class="opportunity-card {sig_class}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
    <div class="opp-ticker {sig_class}">{ticker}</div>
    <span class="badge badge-blue">{sig_label}</span>
  </div>
  <div class="opp-description">{desc}</div>
  <div class="opp-score-label">
    <span>Conviction Score</span>
    <span class="opp-score-num">{score:.0f}</span>
  </div>
  <div class="opp-score-track">
    <div class="opp-score-fill" style="width:{score:.1f}%"></div>
  </div>
</div>""".format(
        sig_class=sig_class,
        ticker=_esc(ticker),
        sig_label=_esc(sig_label),
        desc=_esc(description),
        score=score_val,
    )


# ═════════════════════════════════════════════════════════════════════════════
# METRIC TABLE ROW
# ═════════════════════════════════════════════════════════════════════════════

def metric_table_row(label: str, value: str, color: str | None = None) -> str:
    """Return HTML for a metric table row."""
    val_style = "color:{0};".format(color) if color else ""
    return """
<div class="metric-card">
  <span class="metric-card-label">{label}</span>
  <span class="metric-card-value" style="{style}">{value}</span>
</div>""".format(label=_esc(label), value=_esc(value), style=val_style)


# ═════════════════════════════════════════════════════════════════════════════
# DEBUG EXPANDER
# ═════════════════════════════════════════════════════════════════════════════

def debug_expander(data: dict) -> None:
    """Render JSON data in a collapsed expander with basic syntax highlighting."""
    with st.expander("Debug — dados brutos (JSON)", expanded=False):
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pretty = str(data)
        st.code(pretty, language="json")
