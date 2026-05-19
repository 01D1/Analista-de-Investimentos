"""
Plataforma Quant B3 — App unificado (5 páginas)

Navegação horizontal no topo — funciona em desktop, mobile e Cloudflare.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# força a raiz do scanner no topo
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))

sys.path.insert(0, str(ROOT))

# agora importa normalmente
import streamlit as st

from src.bootstrap import ensure_project_root
ensure_project_root()

from _style import DARK_CSS

# Remove qualquer ocorrência anterior da raiz para recolocar no topo
root_str = str(ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)

# Garante que scanner_quant_profit_b3 venha antes de 12_PYTHON/src
sys.path.insert(0, root_str)

import streamlit as st
from _style import DARK_CSS

try:
    from src.ui.styles import PREMIUM_CSS as _PREMIUM_CSS
except Exception:
    _PREMIUM_CSS = DARK_CSS

st.set_page_config(
    page_title="Plataforma Quant · B3",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS global (premium includes all dark base styles) ───────────────────────
st.markdown(_PREMIUM_CSS, unsafe_allow_html=True)

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
