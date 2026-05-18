"""
test_delivery_telegram.py
--------------------------
Phase 5 - Telegram delivery tests covering DEL-03, DEL-04.

Covers:
  - send_thesis_alert() envia mensagem com ticker, posicionamentos e rationale
  - Alerta dispara apenas quando posicionamento muda
  - Falha no alerta nao levanta excecao (nao bloqueia armazenamento de tese)
  - send_daily_brief() envia mensagem com Selic, PTAX e top movers
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def test_send_thesis_alert_format(monkeypatch):
    """DEL-03: send_thesis_alert() envia texto contendo ticker e novo posicionamento."""
    sent_texts = []

    def mock_send(self, text, **kwargs):
        sent_texts.append(text)
        return True

    monkeypatch.setattr("src.delivery.telegram_bot.TelegramBot.send", mock_send)

    from src.delivery.telegram_bot import TelegramBot

    bot = TelegramBot(token="fake", chat_id="123")
    result = bot.send_thesis_alert(
        ticker="PETR4",
        old_positioning="MANTER",
        new_positioning="COMPRAR",
        confidence="ALTA",
        rationale_one_line="DCF sugere forte desconto ao preco atual.",
        top_opportunity_desc="DCF_DIVERGENCE - upside 35%",
    )

    assert result is True
    assert len(sent_texts) == 1
    assert "PETR4" in sent_texts[0]
    assert "COMPRAR" in sent_texts[0]
    assert "MANTER" in sent_texts[0]


def test_alert_only_on_change(monkeypatch):
    """DEL-03: _maybe_send_thesis_alert() dispara apenas quando posicionamento muda."""
    import sqlite3

    from src.intelligence_layer import _maybe_send_thesis_alert

    sent_count = []

    def mock_send_alert(self, **kwargs):
        sent_count.append(1)
        return True

    monkeypatch.setattr("src.delivery.telegram_bot.TelegramBot.send_thesis_alert", mock_send_alert)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE opportunity_signals "
        "(ticker TEXT, description TEXT, conviction_score INT, computed_date TEXT)"
    )

    # Mesmo posicionamento - nao deve disparar
    _maybe_send_thesis_alert("PETR4", "COMPRAR", "COMPRAR", "ALTA", "one line", conn)
    assert len(sent_count) == 0, "Nao deve disparar alerta quando posicionamento nao muda"

    # Posicionamento anterior None - nao deve disparar
    _maybe_send_thesis_alert("PETR4", "COMPRAR", None, "ALTA", "one line", conn)
    assert len(sent_count) == 0, "Nao deve disparar alerta quando prev_positioning e None"

    conn.close()


def test_alert_failure_does_not_raise(monkeypatch):
    """DEL-03: _maybe_send_thesis_alert() nunca levanta excecao mesmo com bot.send() falhando."""
    import sqlite3

    from src.intelligence_layer import _maybe_send_thesis_alert

    def mock_get_bot():
        bot = MagicMock()
        bot.send_thesis_alert.side_effect = RuntimeError("network error")
        return bot

    monkeypatch.setattr("src.delivery.telegram_bot.get_bot", mock_get_bot)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE opportunity_signals "
        "(ticker TEXT, description TEXT, conviction_score INT, computed_date TEXT)"
    )

    # Posicionamentos diferentes (deveria disparar alerta que vai falhar)
    # Nao deve levantar excecao
    _maybe_send_thesis_alert("PETR4", "COMPRAR", "MANTER", "ALTA", "one line", conn)
    conn.close()


def test_send_daily_brief_format(monkeypatch):
    """DEL-04: send_daily_brief() envia texto com data, Selic, PTAX e movers."""
    sent_texts = []

    def mock_send(self, text, **kwargs):
        sent_texts.append(text)
        return True

    monkeypatch.setattr("src.delivery.telegram_bot.TelegramBot.send", mock_send)

    from src.delivery.telegram_bot import TelegramBot

    bot = TelegramBot(token="fake", chat_id="123")
    macro_snapshot = {"selic": 14.75, "ptax": 5.7821, "ibov_pct": -0.5}
    top_movers = [
        {"ticker": "PETR4", "description": "upside +35.0%", "score": "-"},
        {"ticker": "VALE3", "description": "upside +22.0%", "score": "-"},
        {"ticker": "ITUB4", "description": "upside +18.0%", "score": "-"},
    ]
    result = bot.send_daily_brief(
        macro_snapshot=macro_snapshot,
        top_movers=top_movers,
        top_opportunity=None,
    )

    assert result is True
    assert len(sent_texts) == 1
    text = sent_texts[0]
    # Deve conter dados macro
    assert "14.75" in text or "Selic" in text
    assert "PETR4" in text


# ── WR-07: send_morning_call_summary frontmatter stripping ──────────────────

def test_morning_call_strip_frontmatter(monkeypatch, tmp_path):
    """WR-07: send_morning_call_summary() remove YAML frontmatter corretamente."""
    sent_texts = []

    def mock_send(self, text, **kwargs):
        sent_texts.append(text)
        return True

    monkeypatch.setattr("src.delivery.telegram_bot.TelegramBot.send", mock_send)

    from src.delivery.telegram_bot import TelegramBot

    bot = TelegramBot(token="fake", chat_id="123")

    # Case 1: file with frontmatter — stripped, only body reaches send()
    f1 = tmp_path / "morning_call_2026-05-18.md"
    f1.write_text("---\ntitle: test\ndate: 2026-05-18\n---\nCorpo do resumo aqui.", encoding="utf-8")
    bot.send_morning_call_summary(f1)
    assert len(sent_texts) == 1
    assert "Corpo do resumo aqui." in sent_texts[0]
    assert "title: test" not in sent_texts[0]

    # Case 2: file without frontmatter — full content forwarded
    sent_texts.clear()
    f2 = tmp_path / "morning_call_2026-05-19.md"
    f2.write_text("Sem frontmatter. Conteudo direto.", encoding="utf-8")
    bot.send_morning_call_summary(f2)
    assert len(sent_texts) == 1
    assert "Sem frontmatter. Conteudo direto." in sent_texts[0]

    # Case 3: file where --- appears inside content (not frontmatter closing)
    sent_texts.clear()
    f3 = tmp_path / "morning_call_2026-05-20.md"
    f3.write_text("---\ntitle: test\n---\nCorpo com --- separador horizontal.", encoding="utf-8")
    bot.send_morning_call_summary(f3)
    assert len(sent_texts) == 1
    # Frontmatter must be stripped; body text preserved
    assert "Corpo com" in sent_texts[0]
    assert "title: test" not in sent_texts[0]
