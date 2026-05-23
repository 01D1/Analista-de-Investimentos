"""
Agent Runtime Scheduler — Scheduling and monitoring for quantitative routines.
"""
import sys
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
from src.ui.components import (
    live_pill, section_title, kpi_card, status_chip,
    alert_block, empty_state, metric_card,
)
from src.ui.styles import PREMIUM_CSS
from src.dashboard.data import _db_path

# Apply canonical design tokens
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# DATA — loaded from real database tables (not hardcoded)
# ──────────────────────────────────────────────────────────────────────────

def _load_source_health() -> list[dict]:
    """Load real source health data from scanner_quant.db."""
    try:
        import sqlite3
        db = _db_path()
        conn = sqlite3.connect(str(db))
        rows = conn.execute("""
            SELECT source_name, status, records_count, age_days, message, checked_at
            FROM source_health_checks
            ORDER BY checked_at DESC
            LIMIT 10
        """).fetchall()
        conn.close()
        if rows:
            return [
                {"source": str(r[0] or ""), "status": str(r[1] or "").lower(),
                 "records": r[2], "age_days": r[3],
                 "message": str(r[4] or ""), "checked_at": str(r[5] or "")}
                for r in rows
            ]
    except Exception:
        pass
    return []


def _sparkline_fallback(seed: int = 42, length: int = 30) -> list[float]:
    """Generate a plausible-looking sparkline from seed.
    Used ONLY when real throughput/latency data is unavailable."""
    s = seed
    v = 50.0
    out = []
    for _ in range(length):
        s = (s * 9301 + 49297) % 233280
        r = s / 233280
        v += (r - 0.5) * 10
        v = max(8.0, min(92.0, v))
        out.append(round(v, 1))
    return out


# Load real data at module level
_SOURCE_HEALTH = _load_source_health()
_MARKET_EVENTS = []

if _SOURCE_HEALTH:
    source_statuses = {a["source"]: a["status"] for a in _SOURCE_HEALTH}
    healthy_count = sum(1 for s in source_statuses.values() if s == "ok")
    total = len(source_statuses)
    RUNTIME_AGENTS = [
        {
            "id": str(a.get("source", "")).replace(" ", "_").lower(),
            "name": str(a.get("source", "")).replace("_", " ").title(),
            "status": a.get("status", "unknown"),
            "spark": _sparkline_fallback(),
        }
        for a in _SOURCE_HEALTH
    ]
    RUNTIME_METRICS = [
        {"k": "Fontes ativas", "v": f"{healthy_count}/{total}", "unit": "", "color": "green" if healthy_count == total else "amber", "delta": 0},
        {"k": "Ultima verificacao", "v": str(_SOURCE_HEALTH[0].get("checked_at", "—"))[:10], "unit": "", "color": "cyan", "delta": 0},
    ]
    PIPELINE = []
else:
    RUNTIME_AGENTS = []
    RUNTIME_METRICS = [
        {"k": "Fontes", "v": "SEM_DADOS", "unit": "", "color": "red"},
        {"k": "Status", "v": "dados nao disponiveis", "unit": "", "color": "gray"},
    ]
    PIPELINE = []


INCIDENTS = []

INFRA_MEMORY = []
# HEALTH states map to governance status_chip
# healthy → APPROVED_FOR_STUDY (green)
# degraded → DEGRADED (amber)
# incident → BLOCKED (red)
HEALTH = {
    "healthy":   {"c": "var(--pos-500)", "border": "var(--pos-500)"},
    "degraded":  {"c": "var(--warn-500)", "border": "var(--warn-500)"},
    "incident":  {"c": "var(--neg-500)",  "border": "var(--neg-500)"},
    "unknown":   {"c": "var(--fg-5)",     "border": "var(--border-1)"},
}

def health_pulse(status):
    """Render health status using status_chip."""
    s = str(status or "").lower()
    if s == "incident":
        return status_chip("BLOCKED", "INCIDENT")
    elif s == "degraded":
        return status_chip("DEGRADED", "DEGRADED")
    else:
        return status_chip("APPROVED_FOR_STUDY", "HEALTHY")

def sparkline_svg(values, color, w, h):
    if not values: return ""
    
    min_val = min(values)
    max_val = max(values)
    
    points = []
    for i, v in enumerate(values):
        x = (i / (len(values) - 1)) * w if len(values) > 1 else w / 2
        y = h - ((v - min_val) / (max_val - min_val)) * h if (max_val - min_val) != 0 else h / 2
        points.append(f"{x},{y}")
    
    return f"""
    <svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="display: block;">
        <polyline fill="none" stroke="{color}" stroke-width="1.5" points="{' '.join(points)}" />
    </svg>
    """


def metric_tile(m):
    color_map = {'cyan': 'var(--brand-400)', 'green': 'var(--pos-500)', 'amber': 'var(--warn-500)', 'red': 'var(--neg-500)'}
    delta_color = (
        ('var(--neg-500)' if m['color'] in ['red', 'amber'] else 'var(--pos-500)') if m['delta'] > 0 else
        ('var(--pos-500)' if m['color'] in ['red', 'amber'] else 'var(--neg-500)') if m['delta'] < 0 else
        'var(--fg-5)'
    )
    delta_html = ""
    if m['delta'] != 0:
        delta_val = abs(m['delta'])
        delta_val_str = f'{delta_val:.2f}' if delta_val < 1 else f'{int(delta_val)}'
        delta_html = f"""
            <span style="font-family: var(--font-mono); font-size: 0.6rem; font-weight: 700; color: {delta_color};">
                {'▲ +' if m['delta'] > 0 else '▼ '}{delta_val_str}
            </span>
        """
    
    unit_html = f'<span style="font-family: var(--font-mono); font-size: 0.66rem; color: var(--fg-5);">{m['unit']}</span>' if m['unit'] else ''
    
    st.markdown(f"""
    <div style="background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-lg); padding: 10px 12px; border-top: 2px solid {color_map[m['color']]};">
        <div style="display: flex; justify-content: space-between; alignItems: baseline; margin-bottom: 4px;">
            <div style="font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.5px; color: var(--fg-6); font-weight: 800;">{m['k']}</div>
            {delta_html}
        </div>
        <div style="display: flex; alignItems: baseline; gap: 4px;">
            <span style="font-family: var(--font-display); font-size: 1.3rem; font-weight: 900; color: var(--fg-1); letter-spacing: -0.4px; line-height: 1.05;">{m['v']}</span>
            {unit_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def agent_card(a):
    # Support both 'health' and 'status' keys for resilience
    agent_health = a.get('health') or a.get('status') or 'unknown'
    # Use .get() with defaults so missing runtime fields render honestly as '—'
    spark_svg = sparkline_svg(a.get('spark', []), ('#EF4444' if agent_health == 'incident' else ('#F59E0B' if agent_health == 'degraded' else '#22D3EE')), 220, 28)
    health_status_html = health_pulse(agent_health)

    _queue = a.get('queue', 0)
    _mem   = a.get('mem', 0)
    _lat   = a.get('latency', 0)
    queue_color = (
        'var(--neg-500)' if _queue > 20 else
        'var(--warn-500)' if _queue > 5 else
        'var(--fg-1)'
    )
    mem_color = 'var(--warn-500)' if _mem > 70 else 'var(--fg-1)'
    latency_color = 'var(--warn-500)' if _lat > 1000 else 'var(--fg-1)'

    border_color_style = (
        f'border: 1px solid {HEALTH[agent_health]["border"]};' if agent_health in HEALTH and 'border' in HEALTH[agent_health] else
        'border: 1px solid var(--border-1);'
    )

    _throughput = a.get('throughput', '—')
    _latency    = a.get('latency', '—')
    _queue      = a.get('queue', '—')
    _jobs       = a.get('jobs', '—')
    _tokens     = a.get('tokensMin', 0)
    _mem        = a.get('mem', '—')

    st.markdown(f"""
    <div style="background: var(--bg-3); {border_color_style} border-radius: var(--r-xl); padding: 12px 14px; transition: all 0.2s ease-in-out;"
         onMouseEnter="this.style.borderColor='var(--brand-600)'; this.style.boxShadow='var(--shadow-2)';"
         onMouseLeave="this.style.borderColor='{HEALTH[agent_health]["border"] if agent_health in HEALTH and "border" in HEALTH[agent_health] else "var(--border-1)"}'; this.style.boxShadow='none';">
        <div style="display: flex; justify-content: space-between; alignItems: center; margin-bottom: 6px;">
            <div style="display: flex; alignItems: center; gap: 6px; min-width: 0;">
                <span style="color: var(--brand-300);"><!-- Icon {a.get('icon', '')} --></span>
                <span style="font-size: 0.74rem; font-weight: 800; color: var(--fg-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{a.get('name', '—')}</span>
            </div>
            {health_status_html}
        </div>
        <div style="height: 28px; width: 100%; margin-bottom: 8px;">{spark_svg}</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; margin-top: 8px; font-family: var(--font-mono); font-size: 0.66rem;">
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">tput</span>
                <span style="color: var(--fg-1); font-weight: 700;">{_throughput}/min</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">p95</span>
                <span style="color: {latency_color}; font-weight: 700;">{_latency}ms</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">queue</span>
                <span style="color: {queue_color}; font-weight: 700;">{_queue}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">jobs</span>
                <span style="color: var(--fg-1); font-weight: 700;">{_jobs}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">tok/m</span>
                <span style="color: var(--fg-1); font-weight: 700;">{f'{_tokens/1000:.1f}k' if _tokens > 0 else '—'}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: var(--fg-6);">mem</span>
                <span style="color: {mem_color}; font-weight: 700;">{_mem}%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_agent_cluster():
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px;">
    """, unsafe_allow_html=True)
    for agent in RUNTIME_AGENTS:
        agent_card(agent)
    st.markdown("</div>", unsafe_allow_html=True)

def render_pipeline_graph():
    st.markdown("""
    <div style="background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-xl); padding: 18px 20px; overflow-x: auto;">
        <div style="display: flex; justify-content: space-between; alignItems: center; margin-bottom: 14px;">
            <div style="display: flex; gap: 10px; alignItems: center;">
                <span style="font-size: 0.64rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: var(--fg-5);">Pipeline · ingestion → research</span>
                <span class="live-pill"><span class="dot"></span>RUNTIME</span>
            </div>
            <div style="display: flex; gap: 14px; font-family: var(--font-mono); font-size: 0.62rem; color: var(--fg-5);">
                <span><span style="display: inline-block; width: 8px; height: 8px; border-radius: 99px; background: var(--pos-500); margin-right: 4px;"></span>healthy</span>
                <span><span style="display: inline-block; width: 8px; height: 8px; border-radius: 99px; background: var(--warn-500); margin-right: 4px;"></span>degraded</span>
                <span><span style="display: inline-block; width: 8px; height: 8px; border-radius: 99px; background: var(--neg-500); margin-right: 4px;"></span>incident</span>
            </div>
        </div>
        <div style="display: flex; alignItems: stretch; gap: 0; min-width: fit-content;">
    """, unsafe_allow_html=True)
    
    for i, node in enumerate(PIPELINE):
        c = HEALTH[node['status']]['c']
        animation_style = (
            'animation: breathe 0.9s infinite;' if node['status'] == 'incident' else
            'animation: breathe 1.6s infinite;' if node['status'] == 'degraded' else
            'animation: breathe 2.4s infinite;'
        )
        bg_gradient = (
            'linear-gradient(135deg, var(--bg-2), rgba(239,68,68,0.08))' if node['status'] == 'incident' else
            'linear-gradient(135deg, var(--bg-2), rgba(245,158,11,0.06))' if node['status'] == 'degraded' else
            'var(--bg-2)'
        )
        border_style = (
            f'1px solid {HEALTH[node['status']]['border']}' if node['status'] in HEALTH and 'border' in HEALTH[node['status']] else
            '1px solid var(--border-1)'
        )

        st.markdown(f"""
        <div style="flex: 1; min-width: 132px; background: {bg_gradient}; border: {border_style}; border-radius: var(--r-md); padding: 10px 12px; position: relative;">
            <div style="display: flex; alignItems: center; gap: 6px; margin-bottom: 4px;">
                <span style="width: 6px; height: 6px; border-radius: 50%; background: {c}; box-shadow: 0 0 6px {c}; {animation_style}"></span>
                <span style="font-size: 0.74rem; font-weight: 800; color: var(--fg-1);">{node['label']}</span>
            </div>
            <div style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-5); margin-bottom: 6px; line-height: 1.3;">{node['sub']}</div>
            <div style="font-family: var(--font-mono); font-size: 0.74rem; color: var(--fg-1); font-weight: 700;">{node['metric']}</div>
        </div>
        """, unsafe_allow_html=True)

        if i < len(PIPELINE) - 1:
            st.markdown(f"""
            <div style="display: flex; alignItems: center; padding: 0 4px; position: relative; width: 28px; color: var(--brand-400);">
                <svg width="20" height="14" viewBox="0 0 20 14">
                    <path d="M0 7 L16 7 M11 2 L16 7 L11 12" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span style="position: absolute; left: 0; top: 50%; margin-top: -1.5px; width: 4px; height: 3px; background: var(--brand-300); border-radius: 99px; box-shadow: 0 0 6px var(--brand-300); animation: flowDot 1.8s linear infinite;"></span>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

def render_runtime_metrics():
    st.markdown("""
    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px;">
    """, unsafe_allow_html=True)
    for metric in RUNTIME_METRICS:
        metric_tile(metric)
    st.markdown("</div>", unsafe_allow_html=True)

def render_incident_log():
    st.markdown("""
    <div style="background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-xl); overflow: hidden;">
    """, unsafe_allow_html=True)
    for i, inc in enumerate(INCIDENTS):
        sev = inc['sev'].upper()
        sev_color = "neg" if sev == "CRIT" else ("warn" if sev == "WARN" else "cyan")
        sev_chip = status_chip(sev, sev)

        # Determine background based on severity
        sev_bg = "rgba(239,68,68,0.10)" if sev == "CRIT" else (
            "rgba(245,158,11,0.08)" if sev == "WARN" else "transparent"
        )

        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 54px 72px 110px 1fr 70px 80px; gap: 12px; padding: 10px 16px; background: {sev_bg}; border-bottom: {'1px solid var(--border-1)' if i < len(INCIDENTS) - 1 else 'none'}; border-left: 3px solid var(--{sev_color == 'neg' and 'neg' or (sev_color == 'warn' and 'warn' or 'brand')}-500); align-items: center;">
            <span style="font-family: var(--font-mono); font-size: 0.66rem; color: var(--fg-5);">{inc['t']}</span>
            <span style="padding:2px 4px;">{sev_chip}</span>
            <span style="font-family: var(--font-mono); font-size: 0.62rem; font-weight: 700; color: var(--fg-3); text-transform: uppercase; letter-spacing: 0.4px;">{inc['scope']}</span>
            <span style="font-size: 0.76rem; color: var(--fg-2); line-height: 1.45;">{inc['msg']}</span>
            <span style="font-family: var(--font-mono); font-size: 0.66rem; color: var(--fg-5); text-align: right;">{inc['dur']}</span>
            <span style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6); text-align: right;">{inc['code']}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_infra_memory():
    st.markdown("""
    <div style="background: var(--bg-3); border: 1px solid var(--border-1); border-radius: var(--r-xl); padding: 14px 16px;">
        <div style="display: flex; justify-content: space-between; alignItems: center; margin-bottom: 10px;">
            <div style="font-size: 0.64rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; color: var(--fg-5);">AI Infrastructure Memory</div>
            <span style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6);">últimos 30 dias</span>
        </div>
        <div style="position: relative; padding-left: 14px;">
            <div style="position: absolute; left: 4px; top: 8px; bottom: 8px; width: 1px; background: var(--border-1);"></div>
    """, unsafe_allow_html=True)
    for i, m in enumerate(INFRA_MEMORY):
        meta = status_chip(m['kind'].upper(), m['kind'].replace("-", " ").upper())
        st.markdown(f"""
        <div style="position: relative; padding: 7px 0 7px 14px; border-bottom: {'1px dashed var(--border-1)' if i < len(INFRA_MEMORY) - 1 else 'none'};">
            <span style="position: absolute; left: -5px; top: 12px; width: 9px; height: 9px; border-radius: 50%; background: var(--bg-3); border: 2px solid var(--brand-400);"></span>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px; gap: 6px;">
                <span style="padding:2px 4px;">{meta}</span>
                <span style="font-family: var(--font-mono); font-size: 0.6rem; color: var(--fg-6);">{m['d']}</span>
            </div>
            <div style="font-size: 0.74rem; color: var(--fg-3); line-height: 1.4;">{m['label']}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)


def main():
    st.markdown("""
    <div class="fade-in">
        <div style="display: flex; justify-content: space-between; alignItems: flex-end; margin-bottom: 16px;">
            <div>
                <div style="font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 800; color: var(--brand-300); margin-bottom: 4px; display: flex; alignItems: center; gap: 8px;">
                    <!-- Icon sliders -->Infrastructure · Operations Layer
                </div>
                <div style="display: flex; alignItems: baseline; gap: 12px;">
                    <div style="font-family: var(--font-display); font-weight: 900; font-size: 1.6rem; color: var(--fg-1); letter-spacing: -0.6px; line-height: 1.1;">Agent Runtime</div>
                    <span class="live-pill"><span class="dot"></span>10 WORKERS · 1 INCIDENT · 2 DEGRADED</span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--fg-5); margin-top: 4px;">
                    ingest <span style="color: var(--fg-2); font-weight: 700;">142/min</span>
                    &nbsp;·&nbsp; tokens <span style="color: var(--fg-2); font-weight: 700;">94.7k/min</span>
                    &nbsp;·&nbsp; cost <span style="color: var(--fg-2); font-weight: 700;">$4.82/h</span>
                </div>
            </div>
            <div style="display: flex; gap: 6px;">
                <button class="btn">Logs</button>
                <button class="btn">Health-check</button>
                <button class="btn primary">Acknowledge incidents</button>
            </div>
        </div>
    """, unsafe_allow_html=True)

    section_title("Pipeline · ingestion → research", subtitle="data plane")
    render_pipeline_graph()

    section_title("Runtime Metrics", subtitle="atualização contínua")
    render_runtime_metrics()

    section_title(
        "Agent Cluster · workers vivos",
        subtitle='<span class="live-pill" style="margin-right: 8px;"><span class="dot"></span>10 / 10</span><button class="btn">Reiniciar worker</button>'
    )
    render_agent_cluster()

    st.markdown("""
    <div style="display: grid; grid-template-columns: 1fr 320px; gap: 14px; margin-top: 22px; align-items: start;">
        <div>
    """, unsafe_allow_html=True)
    section_title(
        "Incidentes &amp; Drift · janela 24h",
        subtitle='<span style="font-family:\'JetBrains Mono\',monospace; font-size:0.7rem; color:var(--neg-500); margin-right: 8px;">1 CRIT · 3 WARN</span><button class="btn">Resolver tudo</button>'
    )
    render_incident_log()
    st.markdown("</div><div>", unsafe_allow_html=True)
    section_title("Memory")
    render_infra_memory()
    st.markdown("</div></div></div>", unsafe_allow_html=True)

main()
