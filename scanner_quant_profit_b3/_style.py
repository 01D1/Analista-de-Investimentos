"""Shared dark theme CSS for scanner_quant_profit_b3 pages."""

DARK_CSS: str = """
<style>
section.main > div { padding-top: 0.2rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* ── page_link nav ── */
[data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #64748B !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.3px !important;
    padding: 6px 10px !important;
    text-decoration: none !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
[data-testid="stPageLink"] a:hover {
    background: #1E2D42 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
}
/* ativa pagina atual */
[data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stPageLink"] a[aria-current="page"] {
    background: #0D1F38 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
}

/* ── Widgets globais dark ── */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
div[data-baseweb="input"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
}
input { color: #E2E8F0 !important; }
.stTextInput input, .stNumberInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
.stMultiSelect span[data-baseweb="tag"] {
    background: #1E3A5F !important;
}
.stDateInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
.stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"] { color: #475569 !important; }

/* ── Expanders ── */
details summary {
    background: #111827 !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    padding: 8px 14px !important;
}
details[open] summary { border-radius: 8px 8px 0 0 !important; }
details > div {
    background: #0D1421 !important;
    border: 1px solid #1E2D42 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 12px 14px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid #1E2D42 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 14px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    color: #93C5FD !important;
    border-bottom: 2px solid #3B82F6 !important;
    background: #0D1F38 !important;
}

/* ── Metricas ── */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 12px 14px;
}
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 0.68rem !important; }
[data-testid="stMetricValue"] { color: #F1F5F9 !important; font-size: 1.3rem !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
</style>
"""
