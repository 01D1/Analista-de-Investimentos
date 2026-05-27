"""
Radar Macro · Research OS — App principal (navegação lateral agrupada)

Grupos de navegação:
  🎯 Decisão   — sinais, scanner, opções, matriz, convicção
  🔭 Research  — macro, IA, tese, watchlist, calendário
  📊 Fundamentos — valuation hub e cobertura
  ⚙️  Técnico   — diagnóstico, pipeline, agentes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.bootstrap import ensure_project_root
ensure_project_root()

from src.ui.styles import PREMIUM_CSS as _PREMIUM_CSS

st.set_page_config(
    page_title="Radar Macro · Research OS",
    page_icon="🩵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────────────────────
_SIDEBAR_CSS = """
<style>
/* Sidebar customization */
[data-testid="stSidebar"] {
    background: #0A1220 !important;
    border-right: 1px solid #1E2D42 !important;
    min-width: 220px !important;
    max-width: 240px !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.6rem !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    color: #475569 !important;
    padding: 12px 8px 4px 8px !important;
    margin: 0 !important;
}
/* Nav links in sidebar */
[data-testid="stSidebarNavLink"] {
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    padding: 6px 10px !important;
}
[data-testid="stSidebarNavLink"]:hover {
    background: rgba(34,211,238,0.08) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(34,211,238,0.14) !important;
    color: #22D3EE !important;
    border-left: 2px solid #22D3EE !important;
}
/* Logo area */
.sidebar-logo {
    padding: 16px 12px 12px 12px;
    border-bottom: 1px solid #1E2D42;
    margin-bottom: 8px;
}
/* Hide the default collapse control since sidebar is nav */
[data-testid="collapsedControl"] { display: none; }
</style>
"""

st.markdown(_PREMIUM_CSS + _SIDEBAR_CSS, unsafe_allow_html=True)

# ── Navegação lateral agrupada ────────────────────────────────────────────────
_PAGES = {
    "🎯 Decisão": [
        st.Page("pages/trading_desk.py",             title="Trading Desk",           icon="🎯", default=True),
        st.Page("pages/radar_oportunidades.py",      title="Radar de Oportunidades", icon="📡"),
        st.Page("pages/radar_quant.py",              title="Scanner Quantitativo",   icon="🔬"),
        st.Page("pages/opcoes_monitoramento.py",     title="Opções & Derivativos",   icon="⚡"),
        st.Page("pages/inteligencia_oportunidades.py", title="Matriz de Sinais",     icon="🏆"),
        st.Page("pages/performance.py",              title="Conviction Desk",        icon="📈"),
    ],
    "🔭 Research": [
        st.Page("pages/inteligencia_macro.py",       title="Macro → B3",             icon="🌐"),
        st.Page("pages/radar_ai.py",                 title="Radar AI",               icon="🧠"),
        st.Page("pages/inteligencia_ativo.py",       title="Construtor de Tese",     icon="🧩"),
        st.Page("pages/inteligencia_watchlist.py",   title="Empresas Monitoradas",   icon="👁"),
        st.Page("pages/calendario.py",               title="Calendário Econômico",   icon="📅"),
    ],
    "📊 Fundamentos": [
        st.Page("pages/valuation_engine.py",         title="Valuation Hub",          icon="💎"),
        st.Page("pages/valuation_coverage.py",       title="Cobertura de Valuation", icon="🗺"),
    ],
    "⚙️ Técnico": [
        st.Page("pages/diagnostico_tecnico.py",      title="Diagnóstico Técnico",    icon="🔧"),
        st.Page("pages/agendador.py",                title="Pipeline & Agentes",     icon="🤖"),
    ],
}

nav = st.navigation(_PAGES, position="sidebar")

# ── Logo no sidebar (via st.sidebar) ────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">'
        '<b style="font-family:\'Sora\',sans-serif;font-weight:900;font-size:1rem;'
        'letter-spacing:-0.5px;color:#F1F5F9;">RADAR '
        '<span style="color:#22D3EE">MACRO</span></b>'
        '<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.55rem;'
        'letter-spacing:2px;color:#475569;text-transform:uppercase;margin-top:2px;">'
        'Research OS</div>'
        '</div>',
        unsafe_allow_html=True,
    )

nav.run()
