import streamlit as st

def live_pill(text="LIVE"):
    st.markdown(f'<span class="live-pill"><span class="dot"></span>{text}</span>', unsafe_allow_html=True)

def _escape_html(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def section_title(title, subtitle=None, icon=None):
    """Render a section header with optional subtitle and/or emoji icon.

    Args:
        title: Section heading text.
        subtitle: Optional secondary text (rendered in mono font).
        icon: Optional emoji or character rendered before title (e.g. "📊").
    """
    sub_html = ""
    if subtitle:
        sub_html = f'<span style="font-family:\'JetBrains Mono\',monospace; font-size:0.7rem; color:var(--fg-5);">{subtitle}</span>'
    # Escape all user-supplied strings to prevent XSS
    icon_html = f"{_escape_html(icon)} " if icon else ""
    st.markdown(f"""
    <div class="section-title">
        <span>{icon_html}{_escape_html(title)}</span>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def kpi_card(label, value, delta=None, color="cyan", sub=None):
    delta_html = ""
    if delta:
        if delta > 0:
            delta_html = f'<div class="kpi-delta-pos">▲ +{delta}</div>'
        else:
            delta_html = f'<div class="kpi-delta-neg">▼ {abs(delta)}</div>'
    
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ''
    
    st.markdown(f"""
    <div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
        {sub_html}
    </div>
    """, unsafe_allow_html=True)

def stage_card(label, sub, conf, time, status="done"):
    is_running = status == "running"
    cls = "stage-running" if is_running else ""
    status_dot = f'<span style="width: 6px; height: 6px; border-radius: 50%; background: {"#22D3EE" if is_running else "#22C55E"}; display: inline-block; margin-right: 6px; {"box-shadow: 0 0 8px #22D3EE; animation: breathe 1.4s infinite;" if is_running else ""}"></span>'
    
    st.markdown(f"""
    <div class="card-base {cls}" style="padding: 10px 12px; min-width: 100px;">
        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
            {status_dot}
            <span style="font-size: 0.7rem; font-weight: 800; color: {"var(--brand-300)" if is_running else "var(--fg-2)"};">{label}</span>
        </div>
        <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-5); margin-bottom: 8px; line-height: 1.3;">{sub}</div>
        <div style="display: flex; justify-content: space-between; alignItems: baseline;">
            <span style="font-family: var(--font-display); font-size: 0.95rem; font-weight: 900; color: var(--brand-300);">{conf}</span>
            <span style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6);">{time}</span>
        </div>
        <div style="margin-top: 6px; background: var(--bg-0); border-radius: 99px; height: 2px; overflow: hidden;">
            <div style="height: 100%; width: {conf}%; background: var(--brand-500); border-radius: 99px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    

def hero_section(title=None, subtitle="", ticker=None, nome=None, setor="",
                positioning=None, score=None, upside=None):
    """Render a hero section.

    Supports two modes:
    - Simple: hero_section(title="...", subtitle="...")  [existing]
    - Rich:   hero_section(ticker="PETR4", nome="Petrobras", ...)
    """
    if ticker is not None:
        # Rich mode — display ticker + positioning + score
        title_text = ticker if nome is None else nome
        pos_color = "var(--pos-500)" if str(positioning or "").upper() == "COMPRAR" else (
            "var(--neg-500)" if str(positioning or "").upper() == "VENDER" else "var(--fg-4)"
        )
        pos_str = positioning or ""
        score_str = f"{score:.0f}" if score is not None else "—"
        upside_str = f"{upside:+.1f}%" if upside is not None else ""
        st.markdown(f"""
        <div class="hero-section" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-family:var(--font-display);font-size:1.6rem;font-weight:900;
                         color:var(--fg-1);margin-bottom:2px;">{title_text}</div>
                    <div style="color:var(--fg-4);font-size:.8rem;">{setor}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:var(--font-display);font-weight:900;
                         font-size:1.6rem;color:{pos_color};">{pos_str}</div>
                    <div style="font-family:var(--font-mono);font-size:.72rem;color:var(--fg-5);">
                        Score {score_str}{' · ' + upside_str if upside_str else ''}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        title = title or ""
        st.markdown(f"""
        <div class="hero-section">
            <div style="font-family:var(--font-display);font-size:1.8rem;font-weight:900;
                 color:var(--fg-1);margin-bottom:6px;">{title}</div>
            <div style="color:var(--fg-4);font-size:.82rem;">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)


def kpi_strip(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            kpi_card(
                item.get("label", ""),
                item.get("value", ""),
                item.get("delta"),
                item.get("color", "cyan"),
                item.get("sub"),
            )


def score_gauge(score, label=None):
    score_str = f"{score:.0f}"
    label_html = f'<div style="font-size:.62rem;text-transform:uppercase;letter-spacing:.8px;'
    label_html += f'color:var(--fg-5);margin-bottom:4px;">{label or "SCORE"}</div>'
    st.markdown(f"""
    <div class="panel-shell" style="text-align:center;">
        {label_html}
        <div style="font-family:var(--font-display);font-weight:900;font-size:2.2rem;
             color:var(--brand-300);">{score_str}</div>
    </div>
    """, unsafe_allow_html=True)


def opportunity_card(title=None, ticker="", score="", thesis="",
                    description=None, signal_type=None, conviction_score=None):
    """Render an opportunity card.

    Supports legacy signature:
        opportunity_card(title, ticker, score, thesis)
    And new signature (used by inteligencia_oportunidades.py):
        opportunity_card(ticker="PETR4", description="...", signal_type="BUY",
                        conviction_score=72)
    """
    # Normalize — accept legacy positional + new kwargs
    card_title = str(title) if title else str(ticker or "—")
    card_score = conviction_score if conviction_score is not None else (
        int(score) if score and str(score).isdigit() else (int(score) if score else 0)
    )
    card_desc = _escape_html(description) if description is not None else str(thesis or "")
    score_str = f"{card_score}"
    st.markdown(f"""
    <div class="panel-shell" style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-weight:800;color:var(--fg-1);">{card_title}</div>
                <div style="font-size:.72rem;color:var(--fg-5);">{_escape_html(signal_type) if signal_type else ""}</div>
            </div>
            <div class="badge badge-cyan">{score_str}</div>
        </div>
        <div style="margin-top:10px;color:var(--fg-3);font-size:.78rem;">
            {card_desc}
        </div>
    </div>
    """, unsafe_allow_html=True)



    
def score_breakdown_bars(items):
    """Render score breakdown bars from a dict of {label: value} or list of dicts.

    Supports dict input: score_breakdown_bars({"Valuation": 72.3, "Tecnico": 68.0})
    Also supports list input: score_breakdown_bars([{"label": "Valuation", "value": 72.3, "color": "..."}])
    """
    if isinstance(items, dict):
        items = [{"label": k, "value": v} for k, v in items.items()]

    for item in items:
        label = item.get("label", "")
        value = item.get("value", 0)
        color = item.get("color", "var(--brand-500)")

        st.markdown(f"""
        <div style="margin-bottom:10px;">
            <div style="
                display:flex;
                justify-content:space-between;
                margin-bottom:4px;
                font-size:.72rem;
            ">
                <span style="color:var(--fg-3);">{label}</span>
                <span style="color:var(--fg-1);font-weight:700;">{value}</span>
            </div>

            <div style="
                height:6px;
                background:var(--bg-0);
                border-radius:999px;
                overflow:hidden;
            ">
                <div style="
                    width:{value}%;
                    height:100%;
                    background:{color};
                    border-radius:999px;
                "></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def empty_state(text="Sem dados", icon=""):
    st.markdown(f"""
    <div class="panel-shell" style="
        text-align:center;
        color:var(--fg-5);
        padding:40px 20px;
    ">
        <div style="
            font-size:1.8rem;
            margin-bottom:10px;
        ">
            {_escape_html(icon)}
        </div>

        <div>
            {_escape_html(text)}
        </div>
    </div>
    """, unsafe_allow_html=True)


def thesis_card(title=None, thesis="", score=None, status="Ativa",
                 bull_case=None, bear_case=None, drivers=None, risks=None):
    """Render a thesis card.

    Supports two modes:
    - Simple: thesis_card(title="...", thesis="...", score=72)  [existing]
    - Rich:   thesis_card(bull_case=..., bear_case=..., drivers=[...], risks=[...])
    """
    if bull_case is not None or bear_case is not None:
        # Rich mode
        bull = bull_case or "—"
        bear = bear_case or "—"
        drv_list = drivers or []
        rsk_list = risks or []

        drivers_html = ""
        for d in drv_list:
            impact = str(d.get("impact", "MEDIUM")).upper()
            imp_color = ("var(--pos-500)" if impact == "HIGH" else
                         "var(--warn-500)" if impact == "MEDIUM" else "var(--fg-5)")
            drivers_html += f"""
            <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--border-1);">
                <span style="font-size:.72rem;color:var(--fg-4);flex:1;line-height:1.4;">{d.get('title', '—')}</span>
                <span style="font-size:.65rem;font-weight:700;color:{imp_color};white-space:nowrap;">{d.get('description', '')[:60]}</span>
            </div>"""

        risks_html = ""
        for r in rsk_list:
            sev = str(r.get("severity", "MEDIUM")).upper()
            sev_color = ("var(--neg-500)" if sev == "HIGH" else
                         "var(--warn-500)" if sev == "MEDIUM" else "var(--fg-5)")
            risks_html += f"""
            <div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--border-1);">
                <span style="font-size:.72rem;color:var(--fg-4);flex:1;line-height:1.4;">{r.get('title', '—')}</span>
                <span style="font-size:.65rem;font-weight:700;color:{sev_color};white-space:nowrap;">{r.get('description', '')[:60]}</span>
            </div>"""

        st.markdown(f"""
        <div style="
            background:var(--bg-3);border:1px solid var(--border-1);
            border-radius:var(--r-xl);padding:16px 20px;margin-bottom:14px;
        ">
            <div style="margin-bottom:16px;">
                <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;
                     color:var(--pos-500);font-weight:700;margin-bottom:4px;">BULL CASE</div>
                <div style="font-size:.8rem;color:var(--fg-3);line-height:1.5;">{bull}</div>
            </div>
            <div style="margin-bottom:16px;">
                <div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;
                     color:var(--neg-500);font-weight:700;margin-bottom:4px;">BEAR CASE</div>
                <div style="font-size:.8rem;color:var(--fg-4);line-height:1.5;">{bear}</div>
            </div>
            {('<div style="margin-bottom:12px;"><div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;'
              'color:var(--fg-5);margin-bottom:4px;">DRIVERS</div>' + drivers_html + '</div>') if drivers_html else ''}
            {('<div style="margin-bottom:12px;"><div style="font-size:.65rem;text-transform:uppercase;letter-spacing:.8px;'
              'color:var(--fg-5);margin-bottom:4px;">RISKS</div>' + risks_html + '</div>') if risks_html else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        title = title or ""
        score_html = f'<span style="background:var(--brand-glow-soft);border:1px solid var(--brand-400);'
        score_html += f'border-radius:var(--r-sm);padding:2px 8px;'
        score_html += f'font-size:.65rem;font-weight:800;color:var(--brand-300);">{score}</span>' if score is not None else ""
        st.markdown(f"""
        <div class="panel-shell" style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                <div>
                    <div style="font-weight:900;color:var(--fg-1);font-family:var(--font-display);">
                        {title}
                    </div>
                    <div style="font-size:.72rem;color:var(--fg-5);margin-top:3px;">
                        {status}
                    </div>
                </div>
                {score_html}
            </div>
            <div style="margin-top:10px;color:var(--fg-3);font-size:.78rem;line-height:1.45;">
                {thesis}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
def driver_list(title, items):
    st.markdown(f"""
    <div class="panel-shell" style="margin-bottom:12px;">
        <div style="
            font-weight:900;
            color:var(--fg-1);
            font-family:var(--font-display);
            margin-bottom:10px;
        ">
            {title}
        </div>
    """, unsafe_allow_html=True)

    for item in items:
        if isinstance(item, dict):
            label = item.get("label", item.get("title", ""))
            value = item.get("value", item.get("text", ""))
        else:
            label = str(item)
            value = ""

        st.markdown(f"""
        <div style="
            display:flex;
            justify-content:space-between;
            gap:10px;
            padding:7px 0;
            border-bottom:1px solid var(--border-1);
        ">
            <span style="color:var(--fg-3);font-size:.78rem;">{label}</span>
            <span style="color:var(--fg-5);font-size:.72rem;text-align:right;">{value}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def watchlist_card(asset_row: dict) -> str:
    """Render a watchlist card from a get_watchlist_summary() row dict.

    Args:
        asset_row: dict with keys: ticker, positioning, confidence, fair_value_brl,
                   upside_pct, price, pe_ratio, ev_ebitda, generated_at,
                   valuation_available (S04), valuation_source (S04)
    Returns:
        HTML string to pass to st.markdown(..., unsafe_allow_html=True)
    """
    ticker = str(asset_row.get("ticker", ""))
    positioning = str(asset_row.get("positioning", "")).upper()
    confidence = str(asset_row.get("confidence", ""))
    fv = asset_row.get("fair_value_brl")
    upside = asset_row.get("upside_pct")
    price = asset_row.get("price")
    generated = str(asset_row.get("generated_at", "—"))
    # S04: Valuation enrichment
    val_available = asset_row.get("valuation_available", False)
    val_source = str(asset_row.get("valuation_source", "none"))

    # Color by positioning
    if positioning == "COMPRAR":
        pos_color = "var(--pos-500)"
        pos_bg = "var(--pos-tint)"
    elif positioning == "VENDER":
        pos_color = "var(--neg-500)"
        pos_bg = "var(--neg-tint)"
    else:
        pos_color = "var(--fg-4)"
        pos_bg = "var(--neutral-tint)"

    # Determine upside display, color, and bar width
    try:
        u_val = abs(float(upside)) if upside not in ("", "None", None) else None
    except (TypeError, ValueError):
        u_val = None

    if u_val is not None:
        if u_val > 20:
            upside_color = "var(--pos-500)"
            upside_arrow = "▲"
        elif u_val > 0:
            upside_color = "var(--warn-500)"
            upside_arrow = "▲"
        else:
            upside_color = "var(--neg-500)"
            upside_arrow = "▼"
        upside_str = f"{upside_arrow} {u_val:.1f}%"
    else:
        upside_str = "—"
        upside_color = "var(--fg-5)"
    bar_w = min(max(abs(u_val or 0) * 2, 2), 100)

    fv_str = f"R$ {fv:.2f}" if fv and str(fv) not in ("", "nan", "None") else "—"
    price_str = f"R$ {price:.2f}" if price and str(price) not in ("", "nan", "None") else "—"

    # S04: Valuation badge
    if val_available:
        val_badge = f"""
        <div style="display:inline-block; background:var(--pos-tint); border:1px solid var(--pos-500);
                    border-radius:4px; padding:1px 5px; font-family:var(--font-mono);
                    font-size:.55rem; font-weight:800; color:var(--pos-500);
                    margin-left:6px; vertical-align:middle;">VAL</div>"""
    elif val_source == "scanner_quant_db":
        val_badge = f"""
        <div style="display:inline-block; background:rgba(234,179,8,0.08); border:1px solid var(--warn-500);
                    border-radius:4px; padding:1px 5px; font-family:var(--font-mono);
                    font-size:.55rem; font-weight:800; color:var(--warn-500);
                    margin-left:6px; vertical-align:middle;">SQ</div>"""
    else:
        val_badge = ""

    return f"""
    <div style="
        background: var(--bg-3);
        border: 1px solid var(--border-1);
        border-radius: var(--r-lg);
        padding: 16px 18px;
        margin-bottom: 10px;
        transition: border-color var(--t-fast);
    ">
        <!-- Header row -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
            <div>
                <div style="font-family:var(--font-display); font-weight:900; font-size:1.2rem;
                     color:var(--fg-1); letter-spacing:-0.3px;">{ticker}{val_badge}</div>
                <div style="font-family:var(--font-mono); font-size:0.62rem; color:var(--fg-5);
                     margin-top:2px;">{confidence}</div>
            </div>
            <div style="
                background:{pos_bg};
                border:1px solid {pos_color};
                border-radius:var(--r-sm);
                padding:3px 9px;
                font-family:var(--font-mono);
                font-size:0.65rem;
                font-weight:800;
                color:{pos_color};
            ">{positioning}</div>
        </div>

        <!-- Price / FV row -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px;">
            <div>
                <div style="font-size:0.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:0.6px; margin-bottom:3px;">Preço Atual</div>
                <div style="font-family:var(--font-mono); font-size:0.9rem; font-weight:700;
                     color:var(--fg-1);">{price_str}</div>
            </div>
            <div>
                <div style="font-size:0.58rem; color:var(--fg-6); text-transform:uppercase;
                     letter-spacing:0.6px; margin-bottom:3px;">Valor Justo</div>
                <div style="font-family:var(--font-mono); font-size:0.9rem; font-weight:700;
                     color:var(--fg-1);">{fv_str}</div>
            </div>
        </div>

        <!-- Upside bar -->
        <div style="margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; font-size:0.65rem;
                 color:var(--fg-5); margin-bottom:4px;">
                <span>Upside</span>
                <span style="color:{upside_color}; font-weight:700; font-family:var(--font-mono);">
                    {upside_str}
                </span>
            </div>
            <div style="background:var(--bg-0); border-radius:99px; height:4px; overflow:hidden;">
                <div style="width:{bar_w}%;height:100%;background:{upside_color};border-radius:99px;"></div>
            </div>
        </div>

        <!-- Footer -->
        <div style="font-size:0.58rem; color:var(--fg-6); font-family:var(--font-mono);">
            Atualizado: {generated}
        </div>
    </div>
    """


def risk_item(label: str, description: str = "", severity: str = "MEDIUM") -> str:
    """Render a risk item card.

    Args:
        label: Risk title (e.g. "Governança", "Liquidez")
        description: Risk description text
        severity: HIGH / MEDIUM / LOW — controls border color
    Returns:
        HTML string
    """
    if severity.upper() == "HIGH":
        border_color = "var(--neg-border)"
        dot_color = "var(--neg-500)"
        label_color = "var(--neg-500)"
    elif severity.upper() == "MEDIUM":
        border_color = "var(--warn-border)"
        dot_color = "var(--warn-500)"
        label_color = "var(--warn-500)"
    else:
        border_color = "var(--border-1)"
        dot_color = "var(--fg-5)"
        label_color = "var(--fg-4)"

    return f"""
    <div class="risk-item-base" style="
        background: var(--bg-2);
        border: 1px solid {border_color};
        border-radius: var(--r-md);
        padding: 10px 14px;
        margin-bottom: 8px;
    ">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <span style="
                width:6px; height:6px; border-radius:50%;
                background:{dot_color}; flex-shrink:0;
            "></span>
            <span style="
                font-size:0.7rem; font-weight:700; text-transform:uppercase;
                letter-spacing:0.8px; color:{label_color};
            ">{label}</span>
        </div>
        <div style="font-size:0.76rem; color:var(--fg-4); line-height:1.4;">
            {description}
        </div>
    </div>
    """


def metric_card(label: str, value: str, delta: str | None = None,
                 color: str = "brand", sub: str | None = None) -> str:
    """Render a metric card returning HTML string.

    Args:
        label: Metric label (e.g. "Score PETR4")
        value: Metric value (e.g. "72.37")
        delta: Optional delta string (e.g. "+3.2")
        color: Color key — brand/cyan (cyan), pos (green), neg (red), warn (amber), violet
        sub: Optional sub-label
    Returns:
        HTML string
    """
    color_map = {
        "brand": ("mc-value", "metric-card-brand"),
        "pos":   ("mc-value", "metric-card-pos"),
        "neg":   ("mc-value", "metric-card-neg"),
        "warn":  ("mc-value", "metric-card-warn"),
        "violet":("mc-value", "metric-card-violet"),
        "cyan":  ("mc-value", "metric-card-brand"),
    }
    val_cls, card_cls = color_map.get(color, color_map["brand"])

    delta_html = ""
    if delta:
        is_pos = not str(delta).startswith("-")
        delta_fg = "var(--pos-500)" if is_pos else "var(--neg-500)"
        arrow = "▲" if is_pos else "▼"
        try:
            dval = abs(float(delta))
        except (TypeError, ValueError):
            dval = 0
        delta_html = f'<div class="mc-delta" style="color:{delta_fg};">{arrow} {dval:.1f}</div>'

    sub_html = f'<div class="mc-sub">{sub}</div>' if sub else ""

    return f"""
    <div class="metric-card {card_cls}">
        <div class="mc-label">{label}</div>
        <div class="{val_cls}">{value}</div>
        {delta_html}
        {sub_html}
    </div>
    """


def score_bar(label: str, value: float, color: str = "var(--brand-400)") -> str:
    """Render a score/progress bar returning HTML string.

    Args:
        label: Bar label (e.g. "Score", "Confiança")
        value: 0–100 score value
        color: CSS color variable for the fill
    Returns:
        HTML string
    """
    pct = min(max(float(value), 0), 100)
    return f"""
    <div style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; font-size:0.72rem;
             margin-bottom:4px;">
            <span style="color:var(--fg-3);">{label}</span>
            <span style="color:var(--fg-1); font-weight:700; font-family:var(--font-mono);">
                {pct:.0f}
            </span>
        </div>
        <div style="background:var(--bg-0); border-radius:99px; height:6px; overflow:hidden;">
            <div style="width:{pct}%; height:100%; background:{color}; border-radius:99px;"></div>
        </div>
    </div>
    """


def risk_list(risks: list[dict]) -> None:
    """Render a list of risk items from a list of dicts.

    Args:
        risks: list of dicts with keys: title, description, severity (HIGH/MEDIUM/LOW)
    """
    if not risks:
        st.caption("Sem riscos registrados.")
        return
    for r in risks:
        severity = str(r.get("severity", "MEDIUM")).upper()
        st.markdown(risk_item(
            label=r.get("title", "—"),
            description=r.get("description", "—"),
            severity=severity if severity in ("HIGH", "MEDIUM", "LOW") else "MEDIUM",
        ), unsafe_allow_html=True)


def debug_expander(detail: dict) -> None:
    """Render a collapsible debug panel with full detail dict.

    Args:
        detail: get_asset_detail() response dict
    """
    import json
    with st.expander("🔧 Debug — full asset detail", expanded=False):
        st.json({k: v for k, v in detail.items() if v is not None})


def radar_chart(dimensions: dict[str, float], ticker: str = "") -> "go.Figure":
    """Render a radar/spider chart from dimensions dict.

    Args:
        dimensions: dict of {dimension_name: 0-100 score}
        ticker: optional ticker label
    Returns:
        plotly Figure (imported locally to avoid hard dep)
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    labels = list(dimensions.keys())
    values = list(dimensions.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # close the polygon
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(34,211,238,0.15)",
        line=dict(color="#22D3EE", width=1.5),
        marker=dict(color="#22D3EE", size=5),
        name=ticker or "Score",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 100], gridcolor="#142536", color="#475569"),
            angularaxis=dict(color="#475569"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        height=280,
    )
    return fig


def positioning_badge(positioning: str) -> str:
    """Return HTML string for a positioning badge (COMPRAR/VENDER/MANTER)."""
    pos_upper = str(positioning or "").upper()
    if pos_upper == "COMPRAR":
        cls = "badge badge-buy"
    elif pos_upper == "VENDER":
        cls = "badge badge-sell"
    else:
        cls = "badge badge-hold"
    return f'<span class="{cls}">{positioning}</span>'


def metric_table_row(label: str, value: str, unit: str = "", color: str = "var(--fg-1)") -> str:
    """Return HTML string for a metric table row."""
    return f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border-1);"><span style="font-size:.78rem;color:var(--fg-3);">{label}</span><span style="font-size:.78rem;font-weight:700;font-family:var(--font-mono);color:{color};">{value}{(" " + unit) if unit else ""}</span></div>'


def status_chip(status: str, label: str | None = None) -> str:
    """Return HTML string for a status governance chip.

    Supported status values (case-insensitive):
        DEGRADED             — fonte com problema (amber/warn)
        REVIEW / INTEGRATED_REQUIRES_REVIEW — precisa atenção (violet)
        MONITOR_ONLY         — requer validação contínua (amber)
        MANUAL_REVIEW_READY  — pronto para análise manual (cyan/brand)
        PAPER_ONLY           — apenas para papel (neutral)
        BLOCKED              — rejeitado por regra (neg/red)
        STALE                — dados desatualizados (amber)
        EMPTY                — sem dados (neutral)
        APPROVED_FOR_STUDY / TECH_APPROVED — válido para estudo (pos/green)
        PAPER_READY          — pronto para paper (pos/green)

    Rules enforced (S03 scope):
        - Does NOT transform MONITOR_ONLY into APPROVED.
        - Does NOT hide DEGRADED or stale data.

    Args:
        status: Governance/data status string (uppercase comparison).
        label: Override display label; defaults to uppercase status.
    Returns:
        HTML string for a chip div.
    """
    s = str(status or "").strip()

    # Normalize known aliases
    if s.upper() in ("INTEGRATED_REQUIRES_REVIEW", "REVIEW"):
        chip_cls, label_s = "chip chip-review", label or s.replace("_", " ")
    elif s.upper() == "MONITOR_ONLY":
        chip_cls, label_s = "chip chip-monitor", label or s
    elif s.upper() == "MANUAL_REVIEW_READY":
        chip_cls, label_s = "chip chip-manual", label or "MANUAL REVIEW"
    elif s.upper() == "PAPER_ONLY":
        chip_cls, label_s = "chip chip-paper", label or s
    elif s.upper() == "BLOCKED":
        chip_cls, label_s = "chip chip-blocked", label or s
    elif s.upper() in ("TECH_APPROVED_FOR_STUDY", "APPROVED_FOR_STUDY", "PAPER_READY"):
        chip_cls, label_s = "chip chip-approved", label or "APPROVED"
    elif s.upper() == "STALE":
        chip_cls, label_s = "chip chip-stale", label or s
    elif s.upper() == "EMPTY":
        chip_cls, label_s = "chip chip-empty", label or "SEM DADOS"
    elif s.upper() == "DEGRADED":
        chip_cls, label_s = "chip chip-degraded", label or s
    elif s.upper().startswith("TIER "):
        # e.g. "TIER C" from radar_payload tier field
        chip_cls, label_s = "chip chip-review", label or s.replace("TIER ", "Tier ")
    else:
        # Unknown status — render as neutral chip so it never silently disappears
        chip_cls, label_s = "chip chip-paper", label or s

    return f'<div class="{chip_cls}"><span class="dot"></span>{label_s}</div>'


def alert_block(kind: str, title: str, body: str = "") -> str:
    """Return HTML string for an alert block.

    Args:
        kind: alert-info / alert-warn / alert-error / alert-success
        title: Alert title (rendered bold)
        body: Optional body text
    Returns:
        HTML string
    """
    kind_s = str(kind or "info").lower()
    if kind_s not in ("info", "warn", "error", "success"):
        kind_s = "info"
    body_html = f'<div class="alert-body">{body}</div>' if body else ""
    return f"""
    <div class="alert alert-{kind_s}">
        <div class="alert-title">{title}</div>
        {body_html}
    </div>
    """


def data_table(rows: list[dict], columns: list[str] | None = None) -> str:
    """Render a data table from a list of dicts.

    Args:
        rows: List of dicts with uniform keys
        columns: Optional list of column keys to display (defaults to all keys)
    Returns:
        HTML string for the table
    """
    if not rows:
        return '<div style="color:var(--fg-5); padding:20px; text-align:center;">Sem dados</div>'

    if columns is None:
        columns = list(rows[0].keys())

    # Header
    header_cells = "".join(
        f'<th style="padding:8px 12px; text-align:left; font-size:0.62rem; '
        f'text-transform:uppercase; letter-spacing:0.8px; color:var(--fg-5); '
        f'border-bottom:1px solid var(--border-1);">{c}</th>'
        for c in columns
    )
    header_html = f"<tr>{header_cells}</tr>"

    # Data rows
    row_cells_list = []
    for row in rows:
        cells = "".join(
            f'<td style="padding:8px 12px; font-size:0.78rem; color:var(--fg-2); '
            f'border-bottom:1px solid var(--border-1);">{row.get(c, "—")}</td>'
            for c in columns
        )
        row_cells_list.append(f"<tr>{cells}</tr>")

    return f"""
    <div style="overflow-x:auto; border:1px solid var(--border-1); border-radius:var(--r-lg);">
        <table style="width:100%; border-collapse:collapse;">
            <thead style="background:var(--bg-2);">{header_html}</thead>
            <tbody>{"".join(row_cells_list)}</tbody>
        </table>
    </div>
    """


def filter_bar(filters: list[dict]) -> str:
    """Render a filter bar with filter pills.

    Args:
        filters: list of dicts with keys: label, options (list of str), selected
    Returns:
        HTML string
    """
    items_html = ""
    for f in filters:
        label = f.get("label", "")
        options = f.get("options", [])
        pill_style = (
            "background:var(--brand-glow-soft); border:1px solid var(--brand-400); "
            "color:var(--brand-300); font-weight:700;"
        )
        items_html += f'<span style="display:inline-block; padding:3px 10px; border-radius:var(--r-pill); '
        items_html += f'font-size:0.65rem; {pill_style}">{label}: '
        items_html += f'<strong>{", ".join(str(o) for o in options)}</strong></span>'

    return f"""
    <div style="
        display:flex; flex-wrap:wrap; gap:8px;
        background:var(--bg-2); border:1px solid var(--border-1);
        border-radius:var(--r-lg); padding:10px 14px; margin-bottom:16px;
    ">
        {items_html}
    </div>
    """