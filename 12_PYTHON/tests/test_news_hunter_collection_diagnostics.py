"""Tests for News Hunter collection diagnostics."""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
import types
from pathlib import Path


ROOT = Path(__file__).parent.parent
NEWS_HUNTER = ROOT / "news_hunter"


def _load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _make_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    con.executescript(
        """
        CREATE TABLE noticias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hash TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            link TEXT NOT NULL,
            fonte TEXT,
            categoria TEXT,
            data_coleta TEXT NOT NULL,
            data_pub TEXT,
            conteudo TEXT,
            alertado INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            subcategoria TEXT,
            urgente INTEGER DEFAULT 0,
            resumo_curto TEXT,
            motivo_score TEXT
        );
        CREATE TABLE erros_fonte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fonte TEXT,
            erro TEXT,
            data TEXT
        );
        """
    )
    con.commit()
    con.close()


def test_processar_fonte_reports_success_and_duplicates(monkeypatch, tmp_path):
    db = tmp_path / "banco.db"
    _make_db(db)
    fake_config = types.SimpleNamespace(
        ARQUIVO_LOG=str(tmp_path / "news_hunter.log"),
        USER_AGENT="test-agent",
        PALAVRAS_CHAVE=[],
        EXTRAIR_CONTEUDO=False,
        TIMEOUT_REQUISICAO=1,
        MAX_CHARS_CONTEUDO=100,
        TELEGRAM_ATIVO=False,
        TELEGRAM_TOKEN="",
        TELEGRAM_CHAT_ID="",
        PALAVRAS_ALERTA_IMEDIATO=[],
        SCORE_MINIMO_BOLETIM=0,
        SALVAR_NOTICIAS_SCORE_BAIXO=True,
        ARQUIVO_BANCO=str(db),
        MANTER_DIAS=0,
        IDADE_MAXIMA_PUBLICACAO_DIAS=30,
        FONTES_PRIORITARIAS=[],
        PALAVRAS_EMPRESAS=["mercado"],
        PALAVRAS_TECNOLOGIA=[],
        PALAVRAS_MACRO=["copom", "selic", "juros"],
        PALAVRAS_COMMODITIES=[],
        PALAVRAS_BOLSAS=[],
        PALAVRAS_CRIPTO=[],
        PALAVRAS_CALENDARIO_ECONOMICO=[],
        PALAVRAS_ALERTA_FORTE=[],
    )
    monkeypatch.setitem(sys.modules, "config", fake_config)
    crawler = _load_module("news_hunter_crawler_diag_test", NEWS_HUNTER / "crawler.py")

    class FakeResponse:
        status_code = 200
        content = b"<rss></rss>"

        def raise_for_status(self):
            return None

    entry = types.SimpleNamespace(
        title="Copom e Selic movimentam mercado",
        link="https://example.com/copom",
        summary="Juros e bolsa",
        published="Tue, 26 May 2026 10:00:00 +0000",
    )
    feed = types.SimpleNamespace(
        bozo=False,
        entries=[entry],
        feed=types.SimpleNamespace(title="Fonte Teste"),
    )
    monkeypatch.setattr(crawler, "_baixar_feed", lambda url: FakeResponse())
    monkeypatch.setattr(crawler.feedparser, "parse", lambda content: feed)

    diag1 = crawler.FonteDiagnostico(url="https://feed.test/rss", categoria="financas")
    assert crawler.processar_fonte("https://feed.test/rss", "financas", diagnostico=diag1) == 1
    assert diag1.status == "sucesso"
    assert diag1.entries_total == 1
    assert diag1.novas == 1

    diag2 = crawler.FonteDiagnostico(url="https://feed.test/rss", categoria="financas")
    assert crawler.processar_fonte("https://feed.test/rss", "financas", diagnostico=diag2) == 0
    assert diag2.duplicadas == 1


def test_processar_fonte_filters_stale_publication_dates(monkeypatch, tmp_path):
    db = tmp_path / "banco.db"
    _make_db(db)
    fake_config = types.SimpleNamespace(
        ARQUIVO_LOG=str(tmp_path / "news_hunter.log"),
        USER_AGENT="test-agent",
        PALAVRAS_CHAVE=[],
        EXTRAIR_CONTEUDO=False,
        TIMEOUT_REQUISICAO=1,
        MAX_CHARS_CONTEUDO=100,
        TELEGRAM_ATIVO=False,
        TELEGRAM_TOKEN="",
        TELEGRAM_CHAT_ID="",
        PALAVRAS_ALERTA_IMEDIATO=[],
        SCORE_MINIMO_BOLETIM=0,
        SALVAR_NOTICIAS_SCORE_BAIXO=True,
        ARQUIVO_BANCO=str(db),
        MANTER_DIAS=0,
        IDADE_MAXIMA_PUBLICACAO_DIAS=30,
        FONTES_PRIORITARIAS=[],
        PALAVRAS_EMPRESAS=["mercado"],
        PALAVRAS_TECNOLOGIA=[],
        PALAVRAS_MACRO=["copom", "selic", "juros"],
        PALAVRAS_COMMODITIES=[],
        PALAVRAS_BOLSAS=[],
        PALAVRAS_CRIPTO=[],
        PALAVRAS_CALENDARIO_ECONOMICO=[],
        PALAVRAS_ALERTA_FORTE=[],
    )
    monkeypatch.setitem(sys.modules, "config", fake_config)
    crawler = _load_module("news_hunter_crawler_stale_test", NEWS_HUNTER / "crawler.py")

    class FakeResponse:
        status_code = 200
        content = b"<rss></rss>"

        def raise_for_status(self):
            return None

    entry = types.SimpleNamespace(
        title="Noticia antiga sobre IA e mercado",
        link="https://example.com/old-ai",
        summary="Tecnologia e mercado",
        published="Mon, 24 Jan 2022 12:07:00 +0000",
    )
    feed = types.SimpleNamespace(
        bozo=False,
        entries=[entry],
        feed=types.SimpleNamespace(title="Fonte Antiga"),
    )
    monkeypatch.setattr(crawler, "_baixar_feed", lambda url: FakeResponse())
    monkeypatch.setattr(crawler.feedparser, "parse", lambda content: feed)

    diag = crawler.FonteDiagnostico(url="https://feed.test/rss", categoria="tecnologia")
    assert crawler.processar_fonte("https://feed.test/rss", "tecnologia", diagnostico=diag) == 0
    assert diag.filtradas_data_antiga == 1

    con = sqlite3.connect(str(db))
    assert con.execute("SELECT COUNT(*) FROM noticias").fetchone()[0] == 0
    con.close()


def test_diagnostico_reports_latest_dates(tmp_path):
    db = tmp_path / "banco.db"
    _make_db(db)
    con = sqlite3.connect(str(db))
    con.execute(
        """INSERT INTO noticias
           (hash, titulo, link, fonte, categoria, data_coleta, data_pub, conteudo, score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "hash-1",
            "Noticia recente",
            "https://example.com/news",
            "Fonte",
            "financas",
            "2026-05-26T09:00:00",
            "Tue, 26 May 2026 12:00:00 +0000",
            "",
            10,
        ),
    )
    con.commit()
    con.close()

    diagnostico = _load_module("news_hunter_diagnostico_test", NEWS_HUNTER / "diagnostico.py")
    result = diagnostico.diagnosticar_banco(db)

    assert result["total"] == 1
    assert result["latest_by_data_pub"]["parsed_at"] == "2026-05-26T12:00:00Z"
    assert result["latest_by_data_coleta"]["parsed_at"] == "2026-05-26T09:00:00Z"
