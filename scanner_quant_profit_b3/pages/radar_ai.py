import streamlit as st

from src.ui.styles import PREMIUM_CSS
from src.ui.components import section_title

st.markdown(PREMIUM_CSS, unsafe_allow_html=True)
st.markdown("""
<div class="radar-shell fade-in">
""", unsafe_allow_html=True)


def render_prompt_chain():
    st.markdown("""
    <div class="panel-shell">
        <h3>Prompt Chain</h3>
    </div>
    """, unsafe_allow_html=True)


def render_left_panel():
    st.markdown("""
    <div class="panel-shell">
        <h3>Agent Cluster</h3>
    </div>
    """, unsafe_allow_html=True)


def render_synthesis_card():
    st.markdown("""
    <div class="panel-shell">
        <h3>Synthesis</h3>
    </div>
    """, unsafe_allow_html=True)


def render_reasoning_trace():
    st.markdown("""
    <div class="panel-shell">
        <h3>Reasoning Trace</h3>
    </div>
    """, unsafe_allow_html=True)


def render_conviction_changes():
    st.markdown("""
    <div class="panel-shell">
        <h3>Conviction Changes</h3>
    </div>
    """, unsafe_allow_html=True)


def render_right_panel():
    st.markdown("""
    <div class="panel-shell">
        <h3>Evidence Layer</h3>
    </div>
    """, unsafe_allow_html=True)


def render_agent_map():
    st.markdown("""
    <div class="panel-shell">
        Multi-Agent Market Map
    </div>
    """, unsafe_allow_html=True)


def render_research_feed():
    st.markdown("""
    <div class="panel-shell">
        Intelligence Stream
    </div>
    """, unsafe_allow_html=True)


def main():

    st.markdown("""
    <div style="margin-bottom:18px;">
        <div style="
            font-size:0.7rem;
            color:var(--brand-300);
            text-transform:uppercase;
            letter-spacing:.6px;
            font-weight:800;
        ">
            Research OS · Intelligence Layer
        </div>

        <div style="
            display:flex;
            align-items:center;
            gap:12px;
            margin-top:4px;
        ">
            <div style="
                font-family:var(--font-display);
                font-size:2rem;
                font-weight:900;
                color:var(--fg-1);
            ">
                Radar AI
            </div>

            <span class="live-pill">
                <span class="dot"></span>
                SESSION 0xA34F · PETR4
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_prompt_chain()

    col_left, col_center, col_right = st.columns(
        [1.05, 1.85, 1.15],
        gap="small"
    )

    with col_left:
        render_left_panel()

    with col_center:
        render_synthesis_card()
        render_reasoning_trace()
        render_conviction_changes()

    with col_right:
        render_right_panel()

    section_title(
        "Multi-Agent Market Map"
    )

    render_agent_map()

    section_title(
        "Intelligence Stream"
    )

    render_research_feed()

    st.markdown("</div>", unsafe_allow_html=True)


main()
