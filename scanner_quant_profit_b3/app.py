"""
Plataforma Quant B3 — App unificado (5 páginas)

Navegação horizontal no topo — funciona em desktop, mobile e Cloudflare.
"""
import sys
from pathlib import Path

# Ensure scanner root is on sys.path for _style import
_SCANNER_ROOT = Path(__file__).resolve().parent
if str(_SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCANNER_ROOT))

import streamlit as st
from _style import DARK_CSS  # WR-05: single source of truth for CSS

st.set_page_config(
    page_title="Plataforma Quant · B3",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ── Navegação superior ────────────────────────────────────────────────────────
_PAGES = [
    st.Page("pages/radar_quant.py",      title="Radar Quant",      icon="🎯"),
    st.Page("pages/valuation_engine.py", title="Valuation Engine", icon="📊"),
    st.Page("pages/performance.py",      title="Performance",      icon="📈"),
    st.Page("pages/calendario.py",       title="Calendário",       icon="📅"),
    st.Page("pages/agendador.py",        title="Agendador",        icon="⏱"),
    # Páginas de inteligência (Phase 5 — D-01, D-02)
    st.Page("pages/inteligencia_watchlist.py",    title="Watchlist",    icon="🔭"),
    st.Page("pages/inteligencia_ativo.py",        title="Ativo",        icon="🧠"),
    st.Page("pages/inteligencia_macro.py",        title="Macro",        icon="🌐"),
    st.Page("pages/inteligencia_oportunidades.py", title="Oportunidades", icon="🏆"),
]

# st.navigation DEVE ser chamado antes de st.page_link
pages = st.navigation(_PAGES, position="hidden")

c_logo, *c_navs = st.columns([1.4] + [1] * len(_PAGES))
with c_logo:
    st.markdown(
        '<div style="padding:6px 0 6px 4px;font-size:0.88rem;font-weight:900;'
        'color:#F1F5F9;letter-spacing:-0.5px">'
        'Plataforma <em style="color:#3B82F6">Quant</em> B3</div>',
        unsafe_allow_html=True,
    )

for col, page in zip(c_navs, _PAGES):
    with col:
        st.page_link(page, use_container_width=True)

st.markdown(
    '<hr style="border:0;border-top:1px solid #1E2D42;margin:0 0 4px 0">',
    unsafe_allow_html=True,
)

pages.run()
