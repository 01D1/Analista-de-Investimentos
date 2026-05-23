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

from src.ui.styles import PREMIUM_CSS as _PREMIUM_CSS

st.set_page_config(
    page_title="Radar Macro · Research OS",
    page_icon="🩵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS global (premium includes all dark base styles) ───────────────────────
st.markdown(_PREMIUM_CSS, unsafe_allow_html=True)

# ── Navegação superior ────────────────────────────────────────────────────────

_PAGES = [
    st.Page("pages/radar_ai.py", title="Radar AI", icon="🧠"),

    st.Page(
        "pages/inteligencia_ativo.py",
        title="Construtor de Tese",
        icon="🧩",
    ),

    st.Page(
        "pages/inteligencia_oportunidades.py",
        title="Matriz de Sinais",
        icon="🏆",
    ),

    st.Page(
        "pages/radar_quant.py",
        title="Núcleo Quantitativo",
        icon="🎯",
    ),

    st.Page(
        "pages/valuation_engine.py",
        title="Valuation Engine",
        icon="📊",
    ),

    st.Page(
        "pages/inteligencia_macro.py",
        title="Macro Motor",
        icon="🌐",
    ),

    st.Page(
        "pages/performance.py",
        title="Mesa de Convicção",
        icon="📈",
    ),

    st.Page(
        "pages/agendador.py",
        title="Agent Runtime",
        icon="⚙️",
    ),

    st.Page(
        "pages/calendario.py",
        title="Event Scheduler",
        icon="📅",
    ),

    st.Page(
        "pages/opcoes_monitoramento.py",
        title="Opções Monitor",
        icon="📡",
    ),
]
# st.navigation DEVE ser chamado antes de st.page_link
pages = st.navigation(_PAGES, position="hidden")

c_logo, *c_navs = st.columns([1.6] + [1] * len(_PAGES))
with c_logo:
    st.markdown(
        '<div style="padding:4px 0 8px 4px; display: flex; flex-direction: column; line-height: 1.1;">'
        '<b style="font-family:\'Sora\',sans-serif; font-weight:900; font-size:0.95rem; '
        'letter-spacing:-0.5px; color:#F1F5F9;">RADAR <span style="color:#22D3EE">MACRO</span></b>'
        '<span style="font-family:\'JetBrains Mono\',monospace; font-size:0.55rem; '
        'letter-spacing:2px; color:#475569; text-transform:uppercase;">Research OS</span>'
        '</div>',
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
