# -*- coding: utf-8 -*-
"""
crawler.py — News Hunter
========================
Coletor de notícias: RSS + extração de conteúdo completo + classificação.

Modos de uso:
  python crawler.py               → loop contínuo (Ctrl+C para parar)
  python crawler.py --uma-vez     → executa um ciclo e encerra
  python crawler.py --fonte URL   → processa apenas uma fonte
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

import banco
import classificador
import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
        logging.FileHandler(config.ARQUIVO_LOG, encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger("news_hunter")

SESSAO = requests.Session()
SESSAO.headers.update({"User-Agent": config.USER_AGENT})


# ── Utilitários ───────────────────────────────────────────────────────────────

@dataclass
class FonteDiagnostico:
    url: str
    categoria: str = ""
    status: str = "pendente"
    http_status: int | None = None
    feed_title: str = ""
    entries_total: int = 0
    novas: int = 0
    duplicadas: int = 0
    filtradas_palavra_chave: int = 0
    filtradas_score: int = 0
    filtradas_data_antiga: int = 0
    sem_titulo_ou_link: int = 0
    erro: str = ""
    ultimas_datas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "categoria": self.categoria,
            "status": self.status,
            "http_status": self.http_status,
            "feed_title": self.feed_title,
            "entries_total": self.entries_total,
            "novas": self.novas,
            "duplicadas": self.duplicadas,
            "filtradas_palavra_chave": self.filtradas_palavra_chave,
            "filtradas_score": self.filtradas_score,
            "filtradas_data_antiga": self.filtradas_data_antiga,
            "sem_titulo_ou_link": self.sem_titulo_ou_link,
            "erro": self.erro,
            "ultimas_datas": self.ultimas_datas[:5],
        }


def _baixar_feed(url: str):
    """Baixa RSS com requests para aplicar User-Agent, timeout e erro HTTP claro."""
    resp = SESSAO.get(url, timeout=config.TIMEOUT_REQUISICAO)
    resp.raise_for_status()
    return resp


def _parse_data_publicacao(valor: Any) -> datetime | None:
    """Normaliza datas RSS comuns para UTC, sem quebrar com timezone misto."""
    if not valor:
        return None
    try:
        data = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            data = parsedate_to_datetime(str(valor).strip())
        except (TypeError, ValueError, IndexError):
            return None
    if data.tzinfo is None:
        return data.replace(tzinfo=timezone.utc)
    return data.astimezone(timezone.utc)


def _data_publicacao_antiga(valor: str) -> bool:
    limite_dias = getattr(config, "IDADE_MAXIMA_PUBLICACAO_DIAS", 0)
    if limite_dias <= 0:
        return False
    data = _parse_data_publicacao(valor)
    if data is None:
        return False
    return data < datetime.now(timezone.utc) - timedelta(days=limite_dias)


def _contem_palavra(texto: str) -> bool:
    """Retorna True se o texto contém alguma palavra-chave configurada."""
    if not config.PALAVRAS_CHAVE:
        return True   # sem filtro → aceita tudo
    texto = texto.lower()
    return any(p.lower() in texto for p in config.PALAVRAS_CHAVE)


def _e_alerta_imediato(texto: str) -> bool:
    texto = texto.lower()
    return any(p.lower() in texto for p in config.PALAVRAS_ALERTA_IMEDIATO)


def _extrair_conteudo(url: str) -> str:
    """Baixa a página e extrai texto limpo com BeautifulSoup."""
    if not config.EXTRAIR_CONTEUDO:
        return ""
    try:
        resp = SESSAO.get(url, timeout=config.TIMEOUT_REQUISICAO)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer",
                         "header", "aside", "form", "iframe"]):
            tag.decompose()

        for seletor in ["article", "main", ".content", ".article-body", "body"]:
            bloco = soup.select_one(seletor)
            if bloco:
                texto = bloco.get_text(separator=" ", strip=True)
                return texto[:config.MAX_CHARS_CONTEUDO]

    except Exception as exc:
        logger.debug("Falha ao extrair conteúdo de %s: %s", url, exc)
    return ""


def _enviar_telegram(mensagem: str):
    """Envia alerta via Telegram (se configurado)."""
    if not config.TELEGRAM_ATIVO or not config.TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    try:
        SESSAO.post(
            url,
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": mensagem},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Falha no Telegram: %s", exc)


# ── Core: processar uma fonte RSS ─────────────────────────────────────────────

def processar_fonte(url: str, categoria_fallback: str = "", diagnostico: FonteDiagnostico | None = None) -> int:
    """
    Baixa e processa um feed RSS.
    Retorna o número de notícias NOVAS salvas.
    """
    diag = diagnostico or FonteDiagnostico(url=url, categoria=categoria_fallback)
    try:
        resp = _baixar_feed(url)
        diag.http_status = resp.status_code
        feed = feedparser.parse(resp.content)
    except Exception as exc:
        banco.registrar_erro(url, f"feedparser: {exc}")
        diag.status = "erro"
        diag.erro = str(exc)
        logger.warning("Erro ao parsear feed %s: %s", url, exc)
        return 0

    if feed.bozo and not feed.entries:
        banco.registrar_erro(url, f"feed inválido: {feed.bozo_exception}")
        diag.status = "erro"
        diag.erro = f"feed inválido: {feed.bozo_exception}"
        logger.debug("Feed inválido: %s", url)
        return 0

    nome_fonte = getattr(feed.feed, "title", url)
    diag.feed_title = str(nome_fonte)
    diag.entries_total = len(feed.entries)
    novas = 0

    for entry in feed.entries:
        titulo  = getattr(entry, "title", "").strip()
        link    = getattr(entry, "link",  "").strip()

        if not titulo or not link:
            diag.sem_titulo_ou_link += 1
            continue

        # Filtro por palavras-chave (título primeiro, mais rápido)
        resumo = getattr(entry, "summary", "")
        if not _contem_palavra(titulo) and not _contem_palavra(resumo):
            diag.filtradas_palavra_chave += 1
            continue

        # Data de publicação
        data_pub = ""
        if hasattr(entry, "published"):
            data_pub = entry.published
        elif hasattr(entry, "updated"):
            data_pub = entry.updated
        if data_pub:
            diag.ultimas_datas.append(str(data_pub))
            if _data_publicacao_antiga(data_pub):
                diag.filtradas_data_antiga += 1
                logger.debug("Data de publicação antiga, descartando: %s", titulo[:60])
                continue

        # Hash de deduplicação
        hash_ = banco.gerar_hash(titulo, link)

        # Extração de conteúdo completo
        conteudo = _extrair_conteudo(link)

        # Verificação final de palavras-chave no conteúdo
        texto_completo = titulo + " " + resumo + " " + conteudo
        if not _contem_palavra(texto_completo):
            diag.filtradas_palavra_chave += 1
            continue

        # ── Classificação ─────────────────────────────────────────────────────
        dados_classe = classificador.classificar_noticia(
            titulo=titulo,
            conteudo=conteudo or resumo,
            fonte=nome_fonte,
            link=link,
        )

        # Usa categoria do classificador; fallback = categoria do fontes.txt
        categoria_final = dados_classe["categoria"] or categoria_fallback or "geral"

        # ── Filtro de score mínimo ────────────────────────────────────────────
        if (dados_classe["score"] < config.SCORE_MINIMO_BOLETIM
                and not config.SALVAR_NOTICIAS_SCORE_BAIXO):
            diag.filtradas_score += 1
            logger.debug(
                "Score baixo (%d), descartando: %s",
                dados_classe["score"], titulo[:60]
            )
            continue

        # ── Salvar no banco ───────────────────────────────────────────────────
        nova = banco.salvar(
            hash_, titulo, link, nome_fonte,
            categoria_final, data_pub, conteudo,
            score=dados_classe["score"],
            subcategoria=dados_classe["subcategoria"],
            urgente=dados_classe["urgente"],
            motivo_score=dados_classe["motivo_score"],
        )

        if nova:
            novas += 1
            diag.novas += 1
            logger.info(
                "✦ NOVA [%s|score:%d] %s",
                categoria_final, dados_classe["score"], titulo[:70]
            )

            # Alerta imediato (urgente + telegram)
            if dados_classe["urgente"] or _e_alerta_imediato(titulo + " " + conteudo):
                aviso = f"🚨 ALERTA: {titulo}\n{link}"
                logger.warning(aviso)
                _enviar_telegram(aviso)
                banco.marcar_alertado(hash_)
        else:
            diag.duplicadas += 1

    if diag.status == "pendente":
        diag.status = "sucesso"
    return novas


# ── Leitura das fontes ────────────────────────────────────────────────────────

def carregar_fontes() -> list:
    """
    Lê fontes.txt e retorna lista de (url, categoria).
    Ignora linhas em branco e comentários (#).
    """
    arquivo = Path(config.ARQUIVO_FONTES)
    if not arquivo.exists():
        logger.error("Arquivo de fontes não encontrado: %s", arquivo)
        return []

    fontes = []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        partes = linha.split()
        url       = partes[0]
        categoria = partes[1] if len(partes) > 1 else ""
        fontes.append((url, categoria))
    return fontes


# ── Ciclo de coleta ───────────────────────────────────────────────────────────

def ciclo_completo(limpar_antigas: bool = False) -> dict:
    """Executa uma rodada completa em todas as fontes."""
    fontes = carregar_fontes()
    if not fontes:
        logger.warning("Nenhuma fonte carregada.")
        return {"fontes": 0, "novas": 0}

    total_novas = 0
    diagnosticos: list[FonteDiagnostico] = []
    logger.info("─" * 60)
    logger.info("Ciclo iniciado: %s | %d fontes",
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"), len(fontes))

    for url, categoria in fontes:
        diag = FonteDiagnostico(url=url, categoria=categoria)
        try:
            novas = processar_fonte(url, categoria, diagnostico=diag)
            total_novas += novas
        except Exception as exc:
            diag.status = "erro"
            diag.erro = str(exc)
            logger.error("Erro ao processar fonte %s: %s", url, exc)
        diagnosticos.append(diag)

    if limpar_antigas:
        banco.limpar_antigos()
    else:
        logger.info("Limpeza automatica ignorada; noticias antigas preservadas.")

    stats = banco.estatisticas()
    logger.info(
        "Ciclo concluído: %d novas | total no banco: %d | hoje: %d",
        total_novas, stats["total"], stats["hoje"],
    )
    fontes_sucesso = sum(1 for item in diagnosticos if item.status == "sucesso")
    fontes_erro = sum(1 for item in diagnosticos if item.status == "erro")
    fontes_sem_atualizacao = sum(
        1 for item in diagnosticos
        if item.status == "sucesso" and item.novas == 0
    )
    if fontes_erro:
        logger.warning("Fontes com erro: %d", fontes_erro)
    logger.info(
        "Diagnostico fontes: sucesso=%d | erro=%d | sem_atualizacao=%d",
        fontes_sucesso, fontes_erro, fontes_sem_atualizacao,
    )
    return {
        "fontes": len(fontes),
        "novas": total_novas,
        "fontes_sucesso": fontes_sucesso,
        "fontes_erro": fontes_erro,
        "fontes_sem_atualizacao": fontes_sem_atualizacao,
        "diagnosticos": [item.to_dict() for item in diagnosticos],
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="News Hunter — coletor de notícias")
    p.add_argument("--uma-vez",  action="store_true",
                   help="Executa um ciclo e encerra")
    p.add_argument("--fonte",    default=None,
                   help="Processa apenas esta URL de RSS")
    p.add_argument("--intervalo", type=int, default=None,
                   help=f"Intervalo em segundos (padrão: {config.INTERVALO_SEGUNDOS})")
    args = p.parse_args()

    banco.inicializar()

    intervalo = args.intervalo or config.INTERVALO_SEGUNDOS

    if args.fonte:
        logger.info("Modo: fonte única → %s", args.fonte)
        processar_fonte(args.fonte)
        return

    if args.uma_vez:
        logger.info("Modo: ciclo único")
        ciclo_completo()
        return

    # ── Loop contínuo ─────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("NEWS HUNTER — Loop contínuo")
    logger.info("Palavras-chave: %s", ", ".join(config.PALAVRAS_CHAVE) or "(todas)")
    logger.info("Intervalo: %ds | Fontes: %s", intervalo, config.ARQUIVO_FONTES)
    logger.info("Banco: %s | Ctrl+C para parar", config.ARQUIVO_BANCO)
    logger.info("=" * 60)

    while True:
        try:
            ciclo_completo()
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário.")
            break
        except Exception as exc:
            logger.error("Erro inesperado no ciclo: %s", exc, exc_info=True)

        try:
            logger.info("Aguardando %ds até o próximo ciclo...", intervalo)
            time.sleep(intervalo)
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário.")
            break


if __name__ == "__main__":
    main()
