"""
test_ui_components.py
---------------------
Testes para src/reports/ui_components.py — Phase 49.

Cobre:
  - status_badge() retorna HTML com classes de cor corretas
  - governance_badge() / risk_badge() / data_quality_badge() delegam corretamente
  - empty_state() executa sem erro (mocked Streamlit)
  - command_box() executa sem erro (mocked Streamlit)
  - metric_card() executa sem erro (mocked Streamlit)
  - dataframe_with_status() lida com DataFrame vazio e com status_col ausente
  - Paleta: verde, amarelo, vermelho, cinza
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_st():
    """Retorna mock mínimo do streamlit para renderização de componentes."""
    st = MagicMock()
    st.markdown = MagicMock()
    st.info = MagicMock()
    st.code = MagicMock()
    st.caption = MagicMock()
    st.warning = MagicMock()
    st.dataframe = MagicMock()
    return st


# ---------------------------------------------------------------------------
# status_badge
# ---------------------------------------------------------------------------

class TestStatusBadge:
    def test_green_statuses(self):
        from src.reports.ui_components import status_badge

        for s in ("OK", "APPROVED", "PASS", "CONFIAVEL", "SUCCESS"):
            html = status_badge(s)
            assert "#d4edda" in html, f"Verde esperado para {s}"
            assert "#155724" in html

    def test_yellow_statuses(self):
        from src.reports.ui_components import status_badge

        for s in ("WARNING", "OBSERVATION", "DADOS_INSUFICIENTES", "PENDING_REVIEW"):
            html = status_badge(s)
            assert "#fff3cd" in html, f"Amarelo esperado para {s}"

    def test_red_statuses(self):
        from src.reports.ui_components import status_badge

        for s in ("BLOCKED", "CRITICAL", "FAILED", "REJECTED", "BLOCKED_DATA_QUALITY", "BLOCKED_GOVERNANCE"):
            html = status_badge(s)
            assert "#f8d7da" in html, f"Vermelho esperado para {s}"

    def test_gray_statuses(self):
        from src.reports.ui_components import status_badge

        for s in ("SEM_DADOS", "UNKNOWN", "NOT_RUN", "DRAFT", "ARCHIVED"):
            html = status_badge(s)
            assert "#e2e3e5" in html, f"Cinza esperado para {s}"

    def test_returns_string(self):
        from src.reports.ui_components import status_badge

        result = status_badge("OK")
        assert isinstance(result, str)
        assert "<span" in result

    def test_unknown_status_returns_gray(self):
        from src.reports.ui_components import status_badge

        html = status_badge("TOTALLY_UNKNOWN_STATUS")
        assert "#e2e3e5" in html

    def test_empty_string_handled(self):
        from src.reports.ui_components import status_badge

        html = status_badge("")
        assert isinstance(html, str)

    def test_lowercase_status_normalized(self):
        from src.reports.ui_components import status_badge

        html_lower = status_badge("ok")
        html_upper = status_badge("OK")
        assert html_lower == html_upper


# ---------------------------------------------------------------------------
# Badge aliases
# ---------------------------------------------------------------------------

class TestBadgeAliases:
    def test_governance_badge_delegates(self):
        from src.reports.ui_components import governance_badge, status_badge

        assert governance_badge("BLOCKED") == status_badge("BLOCKED")

    def test_risk_badge_delegates(self):
        from src.reports.ui_components import risk_badge, status_badge

        assert risk_badge("CRITICAL") == status_badge("CRITICAL")

    def test_data_quality_badge_delegates(self):
        from src.reports.ui_components import data_quality_badge, status_badge

        assert data_quality_badge("CONFIAVEL") == status_badge("CONFIAVEL")


# ---------------------------------------------------------------------------
# empty_state
# ---------------------------------------------------------------------------

class TestEmptyState:
    def test_empty_state_no_command(self, monkeypatch):
        from src.reports import ui_components

        mock_st = _mock_st()
        monkeypatch.setattr(ui_components, "st" if hasattr(ui_components, "st") else "__builtins__", mock_st, raising=False)

        # Patch streamlit import inside the function
        import sys
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import empty_state
            empty_state("Mensagem de teste")
            mock_st.info.assert_called_once()
            args = mock_st.info.call_args[0][0]
            assert "Mensagem de teste" in args
        finally:
            del sys.modules["streamlit"]

    def test_empty_state_with_command(self, monkeypatch):
        import sys

        from src.reports import ui_components

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import empty_state
            empty_state("Mensagem", command="python -m src.foo")
            mock_st.info.assert_called_once()
            mock_st.code.assert_called_once()
        finally:
            del sys.modules["streamlit"]


# ---------------------------------------------------------------------------
# command_box
# ---------------------------------------------------------------------------

class TestCommandBox:
    def test_command_box_renders_code(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import command_box
            command_box("python -m src.test --flag")
            mock_st.code.assert_called_once_with("python -m src.test --flag", language="bash")
        finally:
            del sys.modules["streamlit"]

    def test_command_box_with_description(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import command_box
            command_box("python -m src.test", description="Descrição do comando")
            mock_st.markdown.assert_called()
        finally:
            del sys.modules["streamlit"]

    def test_command_box_with_last_run(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import command_box
            command_box("python -m src.test", last_run="2026-05-18")
            mock_st.caption.assert_called()
        finally:
            del sys.modules["streamlit"]


# ---------------------------------------------------------------------------
# dataframe_with_status
# ---------------------------------------------------------------------------

class TestDataframeWithStatus:
    def test_empty_df_shows_empty_state(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import dataframe_with_status
            dataframe_with_status(pd.DataFrame(), "status")
            mock_st.info.assert_called()
            mock_st.dataframe.assert_not_called()
        finally:
            del sys.modules["streamlit"]

    def test_none_df_shows_empty_state(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import dataframe_with_status
            dataframe_with_status(None, "status")
            mock_st.info.assert_called()
        finally:
            del sys.modules["streamlit"]

    def test_df_with_status_col_renders_icons(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import dataframe_with_status

            df = pd.DataFrame([
                {"ticker": "PETR4", "status": "OK"},
                {"ticker": "VALE3", "status": "BLOCKED"},
                {"ticker": "ITUB4", "status": "WARNING"},
            ])
            dataframe_with_status(df, "status")
            mock_st.dataframe.assert_called_once()

            # Verifica que os ícones foram inseridos
            called_df = mock_st.dataframe.call_args[0][0]
            assert "🟢" in called_df["status"].iloc[0]
            assert "🔴" in called_df["status"].iloc[1]
            assert "⚠️" in called_df["status"].iloc[2]
        finally:
            del sys.modules["streamlit"]

    def test_df_without_status_col_renders_plain(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import dataframe_with_status

            df = pd.DataFrame([{"ticker": "PETR4", "valor": 42}])
            dataframe_with_status(df, "status")  # status_col ausente
            mock_st.dataframe.assert_called_once()
        finally:
            del sys.modules["streamlit"]


# ---------------------------------------------------------------------------
# metric_card
# ---------------------------------------------------------------------------

class TestMetricCard:
    def test_metric_card_renders_without_error(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import metric_card
            metric_card("Título", "42", subtitle="linhas", status="OK")
            mock_st.markdown.assert_called()
        finally:
            del sys.modules["streamlit"]

    def test_metric_card_no_status(self, monkeypatch):
        import sys

        mock_st = _mock_st()
        sys.modules["streamlit"] = mock_st  # type: ignore
        try:
            from src.reports.ui_components import metric_card
            metric_card("Título", "99")
            mock_st.markdown.assert_called()
        finally:
            del sys.modules["streamlit"]
