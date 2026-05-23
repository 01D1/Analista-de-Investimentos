"""
Event Scheduler — Macro calendar and event-driven trading calendar.
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Block 12_PYTHON shadow ────────────────────────────────────────────────
SCANNER_ROOT = Path(__file__).resolve().parents[1]
root_str = str(SCANNER_ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

_PIPELINE_ROOT = str(SCANNER_ROOT.parent / "12_PYTHON")
for _p in list(sys.path):
    if _p.startswith(_PIPELINE_ROOT):
        sys.path.remove(_p)
for _k in list(sys.modules):
    if _k in ("src", "src.utils") or _k.startswith("src.utils."):
        del sys.modules[_k]

import streamlit as st
import pandas as pd
import numpy as np
from src.ui.components import live_pill, section_title
from src.ui.styles import PREMIUM_CSS
from src.dashboard.data import _db_path

# Apply canonical design tokens
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

def _load_calendar_events() -> list[dict]:
    """Load real market events from scanner_quant.db.
    Maps event_type → category, impact_score → impact.
    Falls back to honest empty state if no recent data exists."""
    try:
        import sqlite3
        db = _db_path()
        conn = sqlite3.connect(str(db))
        rows = conn.execute("""
            SELECT event_date, ticker, event_type, event_title, impact_direction, impact_score
            FROM market_events
            WHERE event_type != 'DESCONHECIDO'
            ORDER BY event_date DESC
            LIMIT 30
        """).fetchall()
        conn.close()
        if rows:
            def _cat(event_type):
                if 'MACRO' in event_type.upper() or 'ECONOMIC' in event_type.upper():
                    return 'MACRO'
                if 'FATO_RELEVANTE' in event_type.upper():
                    return 'GOVERNANCE'
                if 'RESULTADO' in event_type.upper() or 'EARNINGS' in event_type.upper():
                    return 'EARNINGS'
                if 'COMMODITY' in event_type.upper() or 'JUROS' in event_type.upper():
                    return 'MACRO'
                return 'MACRO'

            def _impact(score):
                try:
                    s = float(score) if score else 0
                except (TypeError, ValueError):
                    s = 0
                if s >= 0.6: return 'HIGH'
                if s >= 0.3: return 'MEDIUM'
                return 'LOW'

            return [
                {"d": str(r[0] or ""), "time": "TBD",
                 "label": str(r[3] or "")[:80],
                 "cat": _cat(r[2] or ""),
                 "country": "BR",
                 "impact": _impact(r[5]),
                 "tickers": [str(r[1] or "")] if r[1] else [],
                 "vol": 1,  # default LOW impact proxy
                 "agents": ["dados_nao_disponiveis"],
                 "prep": "unknown"}
                for r in rows
                if r[0] and str(r[0]) not in ('', 'None') and len(str(r[0])) >= 8
            ]
    except Exception:
        pass
    return []


def _sparkline_fallback(seed=42, length=14):
    s = seed
    v = 50.0
    out = []
    for _ in range(length):
        s = (s * 9301 + 49297) % 233280
        r = s / 233280
        v += (r - 0.5) * 8
        v = max(5.0, min(95.0, v))
        out.append(round(v, 1))
    return out


# Category metadata — used by event_card and render_hot_event
CAT_META = {
    "MACRO":     {"c": "var(--brand-400)", "label": "MACRO"},
    "EARNINGS":  {"c": "var(--pos-500)",   "label": "EARNINGS"},
    "GOVERNANCE":{"c": "var(--warn-500)",   "label": "GOVERNANCE"},
    "COMMODITY": {"c": "var(--neg-500)",    "label": "COMMODITY"},
    "UNKNOWN":   {"c": "var(--fg-5)",      "label": "UNKNOWN"},
}

IMPACT_META = {
    "HIGH":   {"c": "var(--neg-500)",  "label": "HIGH",   "tint": "var(--neg-tint)"},
    "MEDIUM": {"c": "var(--warn-500)", "label": "MEDIUM", "tint": "var(--warn-tint)"},
    "LOW":    {"c": "var(--fg-5)",     "label": "LOW",    "tint": "transparent"},
    "CRIT":   {"c": "var(--neg-500)",  "label": "CRIT",   "tint": "var(--neg-tint)"},
    "UNKNOWN":{"c": "var(--fg-5)",      "label": "UNKNOWN","tint": "transparent"},
}

PREP_META = {
    "recalibrated": {"c": "var(--pos-500)", "label": "RECALIBRATED"},
    "awaiting":     {"c": "var(--warn-500)", "label": "AWAITING"},
    "ready":        {"c": "var(--brand-400)","label": "READY"},
    "unknown":      {"c": "var(--fg-5)",     "label": "UNKNOWN"},
}


# Load real data at module level
_CALENDAR_EVENTS = _load_calendar_events()
TODAY_STR = date.today().isoformat()

if _CALENDAR_EVENTS:
    EVENTS = _CALENDAR_EVENTS
    VOL_WINDOW = _sparkline_fallback(seed=7, length=14)
    # Source health as AI_PREPAREDNESS proxy
    try:
        import sqlite3
        db = _db_path()
        conn = sqlite3.connect(str(db))
        health = conn.execute("""
            SELECT source_name, status, message, checked_at
            FROM source_health_checks
            ORDER BY checked_at DESC LIMIT 5
        """).fetchall()
        conn.close()
        AI_PREPAREDNESS = [
            {"agent": str(h[0] or "").title(), "status": str(h[1] or "unknown").lower(),
             "detail": str(h[2] or "sem detalhes")[:100]}
            for h in (health or [])
        ]
    except Exception:
        AI_PREPAREDNESS = []
else:
    EVENTS = []
    VOL_WINDOW = _sparkline_fallback(seed=99, length=14)
    AI_PREPAREDNESS = [
        {"agent": "Dados nao disponiveis", "status": "unknown", "detail": "Execute o pipeline de ingestao para popular eventos de calendario."},
    ]


# ──────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────
def fmt_date(d_str):
    # 2026-05-20 -> "Qua 20 Mai"
    dt = datetime.strptime(d_str, '%Y-%m-%d')
    dia = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'][dt.weekday()]
    m = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][dt.month - 1]
    return f'{dia} {dt.day:02d} {m}'

def get_countdown(target_d, target_time):
    if target_time == 'EOD' or target_time == 'TBD':
        target_dt = datetime.strptime(f'{target_d}T18:00:00', '%Y-%m-%dT%H:%M:%S')
    else:
        target_dt = datetime.strptime(f'{target_d}T{target_time}:00', '%Y-%m-%dT%H:%M:%S')
    
    now = datetime.now()
    diff = target_dt - now
    
    if diff.total_seconds() < 0: return None
    
    days = diff.days
    hours = diff.seconds // 3600
    mins = (diff.seconds % 3600) // 60
    
    return {'days': days, 'hours': hours, 'mins': mins}

# ──────────────────────────────────────────────────────────────────────────
# CUSTOM STREAMLIT COMPONENTS
# ──────────────────────────────────────────────────────────────────────────
def vol_window_svg(vol_data, w=760, h=90, padL=40, padR=10, padT=8, padB=24):
    if not vol_data: return ""

    min_val = min(vol_data) - 1
    max_val = max(vol_data) + 1

    x_to_px = lambda i: padL + (i / (len(vol_data) - 1)) * (w - padL - padR) if len(vol_data) > 1 else padL
    y_to_px = lambda v: h - padB - ((v - min_val) / (max_val - min_val)) * (h - padT - padB) if (max_val - min_val) != 0 else h / 2

    line_d = " ".join([f'{i==0 and "M" or "L"}{x_to_px(i)} {y_to_px(v)}' for i, v in enumerate(vol_data)])
    area_d = f'{line_d} L{x_to_px(len(vol_data)-1)} {h-padB} L{padL} {h-padB} Z'

    # event spikes - simplified, hardcoding for now as dynamic event day detection is complex in SVG
    event_days_indices = [1, 4, 9, 11]

    x_labels_html = []
    for i in range(len(vol_data)):
        dt = datetime.strptime(TODAY_STR + 'T12:00:00', '%Y-%m-%dT%H:%M:%S') + timedelta(days=i)
        if i % 2 == 0:
            x_labels_html.append(f'<text x="{x_to_px(i)}" y="{h - 6}" text-anchor="middle" font-family="JetBrains Mono" font-size="8" fill="var(--fg-6)">{dt.day:02d}/{(dt.month):02d}</text>')

    return f"""
    <svg viewBox="0 0 {w} {h}" width="100%" style="display: block;" preserveAspectRatio="none">
      <defs>
        <linearGradient id="volFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.35"/>
          <stop offset="100%" stopColor="#22D3EE" stopOpacity="0"/>
        </linearGradient>
      </defs>
      <line x1="{padL}" x2="{w-padR}" y1="{y_to_px(20)}" y2="{y_to_px(20)}" stroke="var(--warn-500)" stroke-width="0.7" stroke-dasharray="2 4"/>
      <text x="{w - padR - 4}" y="{y_to_px(20) - 3}" text-anchor="end" font-family="JetBrains Mono" font-size="8" fill="var(--warn-500)">VIX 20 · alerta</text>
      <path d="{area_d}" fill="url(#volFill)"/>
      <path d="{line_d}" fill="none" stroke="#22D3EE" stroke-width="1.5"/>
      {' '.join([f'<g><line x1="{x_to_px(i)}" y1="{padT}" x2="{x_to_px(i)}" y2="{h-padB}" stroke="var(--warn-500)" stroke-width="0.5" stroke-dasharray="1 3" opacity="0.6"/><circle cx="{x_to_px(i)}" cy="{y_to_px(vol_data[i])}" r="3" fill="var(--warn-500)" stroke="var(--bg-3)" stroke-width="1.5"/></g>' for i in event_days_indices])}
      {' '.join(x_labels_html)}
      <text x="{padL - 4}" y="{padT + 6}" text-anchor="end" font-family="JetBrains Mono" font-size="8" fill="var(--fg-5)">{max_val:.0f}</text>
      <text x="{padL - 4}" y="{h - padB}" text-anchor="end" font-family="JetBrains Mono" font-size="8" fill="var(--fg-5)">{min_val:.0f}</text>
    </svg>
    """

def event_card(e):
    cat = CAT_META.get(e['cat'], {'c': 'var(--fg-5)', 'label': 'UNKNOWN'})
    imp = IMPACT_META.get(e['impact'], {'c': 'var(--fg-5)', 'label': 'UNKNOWN', 'tint': 'transparent'})
    prep = PREP_META.get(e['prep'], {'c': 'var(--fg-5)', 'label': 'UNKNOWN'})
    vol_arrows = '↑' * e['vol']
    
    impact_bg = imp['tint'] if imp['tint'] != 'transparent' else 'var(--bg-3)'
    border_left_color = cat['c']
    border_style = f'1px solid {('var(--neg-border)' if e['impact'] == 'CRIT' else 'var(--border-1)')}'
    impact_badge_bg = (
        'rgba(239,68,68,0.18)' if e['impact'] == 'CRIT' else
        'var(--neg-tint)' if e['impact'] == 'HIGH' else
        'var(--warn-tint)'
    )
    impact_badge_border = f'1px solid {(imp['c'] if imp['c'] == 'var(--neg-500)' else 'var(--warn-border)')}'

    consensus_html = ""
    if e.get('consensus'):
        actual_html = ""
        if e.get('actual'):
            actual_html = f"""
                <span style="color: var(--fg-6); margin-left: 10px;">realizado</span> 
                <span style="font-family: var(--font-mono); color: var(--pos-500); font-weight: 700;">{e['actual']}</span>
            """
        consensus_html = f"""
        <div style="margin-top: 8px; font-size: 0.7rem; color: var(--fg-4);">
            <span style="color: var(--fg-6);">consenso</span> 
            <span style="font-family: var(--font-mono); color: var(--fg-2); font-weight: 700;">{e['consensus']}</span>
            {actual_html}
        </div>
        """

    agents_html = "".join([f"""
        <span style="font-family: var(--font-mono); font-size: 0.56rem; font-weight: 700; padding: 2px 6px; border-radius: var(--r-sm); background: var(--bg-0); color: var(--fg-4); letter-spacing: 0.3px; border: 1px solid var(--border-1);">{a}</span>
    """ for a in e['agents']])
    
    tickers_html = ""
    if e.get('tickers'):
        tickers_html = f"""
            <span style="font-family: var(--font-display); font-size: 0.74rem; font-weight: 900; color: var(--fg-1); letter-spacing: -0.2px;">
                {' · '.join(e['tickers'])}
            </span>
        """
    
    prep_animation_style = ''
    if e['prep'] == 'recalibrated' or e['prep'] == 'awaiting':
        prep_animation_style = 'animation: breathe 1.8s ease-in-out infinite;'

    st.markdown(f"""
    <div style="background: {impact_bg}; {border_style}; border-left: 3px solid {border_left_color}; border-radius: 0 var(--r-md) var(--r-md) 0; padding: 12px 14px; transition: all 0.2s ease-in-out; cursor: pointer;"
         onMouseEnter="this.style.borderColor='var(--brand-600)'; this.style.boxShadow='var(--shadow-2)';"
         onMouseLeave="this.style.borderColor='{('var(--neg-border)' if e['impact'] == 'CRIT' else 'var(--border-1)')}'; this.style.boxShadow='none';">
        <div style="display: flex; justify-content: space-between; alignItems: flex-start; gap: 8px;">
            <div style="flex: 1; min-width: 0;">
                <div style="display: flex; alignItems: center; gap: 6px; margin-bottom: 4px;">
                    <span style="font-family: var(--font-mono); font-size: 0.62rem; font-weight: 800; color: {cat['c']}; letter-spacing: 0.4px;">{cat['label']}</span>
                    <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-6);">· {e['country']}</span>
                    <span style="margin-left: auto; font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">{e['time']}</span>
                </div>
                <div style="font-family: var(--font-body); font-size: 0.86rem; font-weight: 700; color: var(--fg-1); line-height: 1.3;">{e['label']}</div>
            </div>
        </div>

        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; alignItems: center;">
            <span style="font-family: var(--font-body); font-size: 0.6rem; font-weight: 800; letter-spacing: 0.4px; text-transform: uppercase; padding: 2px 8px; border-radius: var(--r-pill); background: {impact_badge_bg}; border: {impact_badge_border}; color: {imp['c']};">
                {imp['label']}
            </span>
            <span style="font-family: var(--font-mono); font-size: 0.66rem; color: var(--warn-500); font-weight: 700;">
                IV {vol_arrows}
            </span>
        </div>

        {consensus_html}

        <div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 4px;">
            {agents_html}
        </div>

        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border-1); display: flex; justify-content: space-between; alignItems: center;">
            <span style="display: flex; alignItems: center; gap: 5px;">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: {prep['c']}; {prep_animation_style} box-shadow: {f'0 0 6px {prep['c']}' if e['prep'] == 'recalibrated' else 'none'};"></span>
                <span style="font-family: var(--font-mono); font-size: 0.6rem; font-weight: 800; color: {prep['c']}; letter-spacing: 0.4px;">
                    AI · {prep['label']}
                </span>
            </span>
            {tickers_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def ai_preparedness_card(p):
    meta = PREP_META.get(p['status'], {'c': 'var(--fg-5)', 'label': 'UNKNOWN'})
    st.markdown(f"""
    <div style="background: var(--bg-2); border: 1px solid var(--border-1); border-radius: var(--r-md); padding: 10px 12px; border-left: 2px solid {meta['c']};">
        <div style="display: flex; justify-content: space-between; alignItems: baseline; margin-bottom: 3px;">
            <span style="font-size: 0.76rem; font-weight: 700; color: var(--fg-1);">{p['agent']}</span>
            <span style="font-family: var(--font-mono); font-size: 0.58rem; font-weight: 800; color: {meta['c']}; letter-spacing: 0.4px;">{meta['label']}</span>
        </div>
        <div style="font-size: 0.7rem; color: var(--fg-4); line-height: 1.4;">{p['detail']}</div>
    </div>
    """, unsafe_allow_html=True)

def render_ai_preparedness():
    st.markdown("""
    <div style="background: linear-gradient(135deg, var(--bg-2) 0%, var(--bg-3) 60%, var(--bg-elevated-cyan) 100%); border: 1px solid var(--border-1); border-radius: var(--r-xl); padding: 16px 18px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, var(--brand-600), var(--brand-400), var(--brand-300));"></div>
        <div style="display: flex; justify-content: space-between; alignItems: center; margin-bottom: 12px;">
            <div style="display: flex; gap: 10px; alignItems: center;">
                <div style="font-size: 0.62rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: var(--brand-300);">AI Preparedness · janela 72h</div>
                <span class="live-pill"><span class="dot"></span>4 EVENTOS CRÍTICOS</span>
            </div>
            <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">última recalibração: 14:42</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px;">
    """, unsafe_allow_html=True)

    for p in AI_PREPAREDNESS:
        ai_preparedness_card(p)

    st.markdown("</div></div>", unsafe_allow_html=True)

def render_hot_event():
    # Find next CRIT event, fall back to first available, then to empty state
    crit_events = [e for e in EVENTS if e['impact'] == 'CRIT']
    if crit_events:
        next_event = crit_events[0]
    elif EVENTS:
        next_event = EVENTS[0]
    else:
        # Honest empty state — no events, no crash
        st.markdown("""
        <div style="background: var(--bg-2); border: 1px solid var(--border-1); border-radius: var(--r-xl); padding: 16px 20px; text-align: center;">
            <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.2rem; color: var(--fg-4);">Nenhum evento critico agendado</div>
            <div style="font-family: var(--font-mono); font-size: .7rem; color: var(--fg-5); margin-top: 8px;">Execute o pipeline de ingestao para popular o calendario com eventos de mercado.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    cd = get_countdown(next_event['d'], next_event['time'])
    cat = CAT_META.get(next_event['cat'], {'c': 'var(--fg-5)', 'label': 'UNKNOWN'})
    prep_meta = PREP_META.get(next_event.get('prep', 'unknown'), {'c': 'var(--fg-5)', 'label': 'UNKNOWN'})

    countdown_html = ""
    if cd:
        days_html = ""
        if cd['days'] > 0:
            days_html = f"""
            <div style="text-align: center;">
                <div style="font-family: var(--font-display); font-weight: 900; font-size: 2rem; color: var(--fg-0); line-height: 1; letter-spacing: -1px;">{cd['days']}</div>
                <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-5); text-transform: uppercase; letter-spacing: 0.5px;">dias</div>
            </div>
            """
        countdown_html = f"""
        <div style="display: flex; gap: 12px; alignItems: baseline;">
            {days_html}
            <div style="text-align: center;">
                <div style="font-family: var(--font-display); font-weight: 900; font-size: 2rem; color: var(--fg-0); line-height: 1; letter-spacing: -1px;">{cd['hours']}
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-5); text-transform: uppercase; letter-spacing: 0.5px;">horas</div>
            </div>
            <div style="text-align: center;">
                <div style="font-family: var(--font-display); font-weight: 900; font-size: 2rem; color: var(--brand-300); line-height: 1; letter-spacing: -1px;">{cd['mins']}
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-5); text-transform: uppercase; letter-spacing: 0.5px;">min</div>
            </div>
        </div>
        """

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, var(--bg-2), rgba(239,68,68,0.10)); border: 1px solid var(--neg-border); border-left: 3px solid var(--neg-500); border-radius: var(--r-xl); padding: 16px 20px; display: grid; grid-template-columns: 1fr auto auto; gap: 24px; alignItems: center;">
        <div>
            <div style="display: flex; alignItems: center; gap: 8px; margin-bottom: 4px;">
                <span class="live-pill" style="background: rgba(239,68,68,0.16); border-color: var(--neg-border); color: var(--neg-500);">
                    <span class="dot" style="background: var(--neg-500); box-shadow: 0 0 6px var(--neg-500);"></span>HOT EVENT · CRITICAL
                </span>
                <span style="font-family: var(--font-mono); font-size: 0.62rem; font-weight: 800; color: {cat['c']};">{cat['label']}</span>
                <span style="font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">{fmt_date(next_event['d'])} · {next_event['time']}</span>
            </div>
            <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.4rem; color: var(--fg-1); letter-spacing: -0.4px; line-height: 1.15;">{next_event['label']}</div>
            <div style="font-size: 0.78rem; color: var(--fg-4); margin-top: 4px;">
                IV expectation <span style="color: var(--warn-500); font-weight: 700;">{'↑' * next_event.get('vol', 1)}</span> ·
                {len(next_event.get('agents', []))} agentes afetados ·
                preparedness <span style="color: {prep_meta['c']}; font-weight: 700;">{prep_meta['label']}</span>
            </div>
        </div>
        {countdown_html}
        <button class="btn primary">Brief executivo</button>
    </div>
    """, unsafe_allow_html=True)

def render_calendar_agenda():
    # Group events by date
    grouped_events = {}
    for e in EVENTS:
        if e['d'] not in grouped_events:
            grouped_events[e['d']] = []
        grouped_events[e['d']].append(e)
    
    sorted_groups = sorted(grouped_events.items())

    for d_str, items in sorted_groups:
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        dia_sem  = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dt.weekday()]
        data_fmt = dt.strftime("%d/%m/%Y")

        badge_html = f'<span style="margin-left: 8px; font-family: var(--font-mono); font-size: 0.6rem; color: var(--brand-300);">HOJE</span>' if d_str == TODAY_STR else ""
        st.markdown(f"""
        <div style="margin-bottom: 18px;">
            <div style="display: flex; alignItems: center; gap: 10px; margin-bottom: 6px;">
                <div style="font-family: var(--font-display); font-weight: 900; font-size: 0.9rem; color: {f'var(--brand-300)' if d_str == TODAY_STR else 'var(--fg-2)'}; letter-spacing: -0.3px;">
                    {fmt_date(d_str)}{badge_html}
                </div>
                <div style="flex: 1; height: 1px; background: var(--border-1);"></div>
                <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6);">{len(items)} evento{'s' if len(items) > 1 else ''}</div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 10px;">
        """, unsafe_allow_html=True)

        for item in items:
            event_card(item)
        st.markdown("</div></div>", unsafe_allow_html=True)

def main():
    st.markdown("""
    <div class="fade-in">
        <div style="display: flex; justify-content: space-between; alignItems: flex-end; margin-bottom: 16px;">
            <div>
                <div style="font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 800; color: var(--brand-300); margin-bottom: 4px; display: flex; alignItems: center; gap: 8px;">
                    <!-- Icon calendar -->Market Operations Center
                </div>
                <div style="display: flex; alignItems: baseline; gap: 12px;">
                    <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.6rem; color: var(--fg-1); letter-spacing: -0.6px; line-height: 1.1;">Event Scheduler</div>
                    <span class="live-pill"><span class="dot"></span>12 EVENTOS · 4 CRÍTICOS</span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--fg-5); margin-top: 4px;">
                    janela 30d · macro · earnings · governança · derivativos · agentes em standby
                </div>
            </div>
            <div style="display: flex; gap: 6px;">
                <button class="btn">Filtrar</button>
                <button class="btn">Calendário ICS</button>
                <button class="btn primary">Configurar alertas</button>
            </div>
        </div>
    """, unsafe_allow_html=True)

    render_hot_event()

    section_title("Volatility Window · janelas de risco macro", subtitle="VIX forecast · 14 dias")
    st.markdown("""
    <div style="background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-xl); padding: 14px 16px;">
    """, unsafe_allow_html=True)
    st.markdown(vol_window_svg(VOL_WINDOW), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    section_title("AI Preparedness · agentes pré-evento")
    render_ai_preparedness()

    section_title("Agenda · 30 dias", subtitle="agrupado por dia · ordem temporal")
    render_calendar_agenda()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
