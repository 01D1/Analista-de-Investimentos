"""
ui_components.py
----------------
Componentes visuais padronizados — Mesa Quant Institucional (Streamlit).

Paleta de status:
  Verde  : OK, APPROVED, PASS, CONFIAVEL, SUCCESS
  Azul   : APPROVED_FOR_INTERNAL_USE, RUNNING
  Amarelo: WARNING, OBSERVATION, DADOS_INSUFICIENTES, PENDING_REVIEW
  Vermelho: BLOCKED, CRITICAL, FAILED, REJECTED, BLOCKED_*
  Cinza  : SEM_DADOS, UNKNOWN, NOT_RUN, DRAFT, ARCHIVED

Uso interno. Não constitui recomendação de investimento. CVM IN 598.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, tuple[str, str, str]] = {
    # icon, bg_color, text_color
    # Verde
    "OK": ("🟢", "#d4edda", "#155724"),
    "APPROVED": ("✅", "#d4edda", "#155724"),
    "APPROVED_FOR_DISTRIBUTION": ("✅", "#d4edda", "#155724"),
    "PASS": ("✅", "#d4edda", "#155724"),
    "CONFIAVEL": ("✅", "#d4edda", "#155724"),
    "SUCCESS": ("✅", "#d4edda", "#155724"),
    # Azul
    "APPROVED_FOR_INTERNAL_USE": ("🔵", "#cce5ff", "#004085"),
    "RUNNING": ("🔄", "#cce5ff", "#004085"),
    # Amarelo
    "WARNING": ("⚠️", "#fff3cd", "#856404"),
    "OBSERVATION": ("⚠️", "#fff3cd", "#856404"),
    "DADOS_INSUFICIENTES": ("⚠️", "#fff3cd", "#856404"),
    "EM_OBSERVACAO": ("⚠️", "#fff3cd", "#856404"),
    "PENDING_REVIEW": ("⏳", "#fff3cd", "#856404"),
    "COMPLETED_WITH_FAILURES": ("⚠️", "#fff3cd", "#856404"),
    # Vermelho
    "BLOCKED": ("🔴", "#f8d7da", "#721c24"),
    "CRITICAL": ("🔴", "#f8d7da", "#721c24"),
    "FAILED": ("❌", "#f8d7da", "#721c24"),
    "REJECTED": ("❌", "#f8d7da", "#721c24"),
    "BLOCKED_DATA_QUALITY": ("🔴", "#f8d7da", "#721c24"),
    "BLOCKED_GOVERNANCE": ("🔴", "#f8d7da", "#721c24"),
    # Cinza
    "SEM_DADOS": ("⬜", "#e2e3e5", "#383d41"),
    "UNKNOWN": ("❓", "#e2e3e5", "#383d41"),
    "NOT_RUN": ("⬜", "#e2e3e5", "#383d41"),
    "DRAFT": ("📝", "#e2e3e5", "#383d41"),
    "ARCHIVED": ("📦", "#e2e3e5", "#383d41"),
    "SEM_REVISAO": ("⬜", "#e2e3e5", "#383d41"),
}

_DEFAULT_STYLE = ("❓", "#e2e3e5", "#383d41")


def _resolve(status: str) -> tuple[str, str, str]:
    key = (status or "UNKNOWN").upper().replace(" ", "_")
    return _STATUS_MAP.get(key, _DEFAULT_STYLE)


# ---------------------------------------------------------------------------
# Badge components (return HTML strings — use with st.markdown unsafe_allow_html)
# ---------------------------------------------------------------------------

def status_badge(status: str) -> str:
    """Retorna HTML de badge colorido para o status dado."""
    icon, bg, fg = _resolve(status)
    label = (status or "—").replace("_", " ").title()
    return (
        f'<span style="background:{bg};color:{fg};'
        f'padding:3px 10px;border-radius:12px;font-size:0.82em;font-weight:600;">'
        f"{icon} {label}</span>"
    )


def governance_badge(status: str) -> str:
    return status_badge(status)


def risk_badge(status: str) -> str:
    return status_badge(status)


def data_quality_badge(status: str) -> str:
    return status_badge(status)


# ---------------------------------------------------------------------------
# Card and layout components
# ---------------------------------------------------------------------------

def metric_card(
    title: str,
    value: Any,
    subtitle: str = None,
    status: str = None,
) -> None:
    """Renderiza card de métrica com cor de status opcional."""
    import streamlit as st

    _, bg, fg = _resolve(status) if status else ("", "#f8f9fa", "#212529")
    body = (
        f'<div style="background:{bg};padding:16px 20px;border-radius:10px;'
        f'margin:4px 0;border-left:4px solid {fg};">'
        f'<div style="font-size:0.75em;color:{fg};opacity:0.75;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.06em;">{title}</div>'
        f'<div style="font-size:1.9em;font-weight:800;color:{fg};margin:4px 0;">{value}</div>'
    )
    if subtitle:
        body += f'<div style="font-size:0.78em;color:{fg};opacity:0.65;">{subtitle}</div>'
    body += "</div>"
    st.markdown(body, unsafe_allow_html=True)


def command_box(
    command: str,
    description: str = None,
    when_to_use: str = None,
    last_run: str = None,
) -> None:
    """Renderiza bloco de comando operacional com metadados."""
    import streamlit as st

    if description:
        st.markdown(f"**{description}**")
    if when_to_use:
        st.caption(f"Quando usar: {when_to_use}")
    st.code(command, language="bash")
    if last_run:
        st.caption(f"Último run: {last_run}")


def empty_state(message: str, command: str = None) -> None:
    """Renderiza estado vazio padronizado com comando sugerido opcional."""
    import streamlit as st

    st.info(f"⬜ {message}")
    if command:
        st.code(command, language="bash")


def warning_panel(title: str, message: str) -> None:
    """Renderiza painel de aviso padronizado."""
    import streamlit as st

    st.warning(f"**{title}:** {message}")


def executive_summary_box(text: str) -> None:
    """Renderiza caixa de resumo executivo."""
    import streamlit as st

    st.info(f"📋 **Resumo Executivo:** {text}")


def dataframe_with_status(df: pd.DataFrame, status_col: str) -> None:
    """Renderiza DataFrame adicionando ícone de status na coluna especificada."""
    import streamlit as st

    if df is None or df.empty:
        empty_state("Nenhum dado disponível.")
        return

    display = df.copy()
    if status_col in display.columns:
        def _icon(v: Any) -> str:
            icon, _, _ = _resolve(str(v) if v else "UNKNOWN")
            return f"{icon} {v}"

        display[status_col] = display[status_col].apply(_icon)

    st.dataframe(display, use_container_width=True)


# ---------------------------------------------------------------------------
# Section header helper
# ---------------------------------------------------------------------------

def section_header(title: str, subtitle: str = None) -> None:
    """Renderiza cabeçalho de seção institucional."""
    import streamlit as st

    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()
