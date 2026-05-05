"""
Plataforma Quant B3 — App unificado
Radar Quant (opções) + Valuation Engine (fundamentos)
"""
import streamlit as st

st.set_page_config(
    page_title="Plataforma Quant · B3",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = st.navigation(
    [
        st.Page("pages/radar_quant.py",      title="Radar Quant",      icon="🎯"),
        st.Page("pages/valuation_engine.py", title="Valuation Engine", icon="📊"),
    ],
    position="sidebar",
)
pages.run()
