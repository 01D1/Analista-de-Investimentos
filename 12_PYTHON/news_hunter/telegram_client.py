# -*- coding: utf-8 -*-
"""
telegram_client.py — News Hunter
==================================
Cliente Telegram para envio de mensagens e boletins.

Envia texto puro (sem Markdown/HTML) para evitar erros de parsing.
Divide automaticamente mensagens longas em partes.
Nunca interrompe o programa principal em caso de falha.

Uso:
    from telegram_client import enviar_boletim, enviar_mensagem
    enviar_boletim(conteudo_do_boletim)
    enviar_mensagem("Mensagem simples de teste")
"""

import logging
import importlib.util
from pathlib import Path
import time

import requests

import config as _ambient_config


def _load_local_config():
    local_path = Path(__file__).with_name("config.py")
    if Path(getattr(_ambient_config, "__file__", "")).resolve() == local_path.resolve():
        return _ambient_config
    spec = importlib.util.spec_from_file_location("news_hunter_local_config", local_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


config = _load_local_config()

logger = logging.getLogger("news_hunter.telegram")

# URL base da API do Telegram
_API_URL = "https://api.telegram.org/bot{token}/{metodo}"

# Pausa entre partes para respeitar rate limit do Telegram (20 msg/min por chat)
_PAUSA_ENTRE_PARTES = 1.5  # segundos


# ── Verificação de configuração ───────────────────────────────────────────────

def telegram_configurado() -> bool:
    """
    Retorna True se TELEGRAM_ATIVO=True e TOKEN + CHAT_ID estiverem preenchidos.
    """
    ativo  = getattr(config, "TELEGRAM_ATIVO", False)
    token  = getattr(config, "TELEGRAM_TOKEN", "").strip()
    chatid = getattr(config, "TELEGRAM_CHAT_ID", "").strip()
    return bool(ativo and token and chatid)


# ── Divisão de texto ──────────────────────────────────────────────────────────

def dividir_texto(texto: str, limite: int = None) -> list:
    """
    Divide texto longo em partes respeitando o limite de caracteres.
    Tenta sempre quebrar em linhas completas para não cortar frases.

    Args:
        texto:  Conteúdo a dividir.
        limite: Tamanho máximo por parte (padrão: config.TELEGRAM_MAX_CHARS).

    Returns:
        Lista de strings, cada uma dentro do limite.
    """
    if limite is None:
        limite = getattr(config, "TELEGRAM_MAX_CHARS", 3900)

    if len(texto) <= limite:
        return [texto]

    partes = []
    linhas = texto.splitlines(keepends=True)  # preserva \n
    parte_atual = ""

    for linha in linhas:
        # Se a linha sozinha já excede o limite, divide na força
        if len(linha) > limite:
            if parte_atual:
                partes.append(parte_atual.rstrip())
                parte_atual = ""
            # Quebra a linha longa em pedaços
            for i in range(0, len(linha), limite):
                partes.append(linha[i:i + limite].rstrip())
            continue

        # Se adicionar a linha estourar o limite, fecha a parte atual
        if len(parte_atual) + len(linha) > limite:
            partes.append(parte_atual.rstrip())
            parte_atual = linha
        else:
            parte_atual += linha

    if parte_atual.strip():
        partes.append(parte_atual.rstrip())

    return [p for p in partes if p.strip()]


# ── Envio de mensagem simples ─────────────────────────────────────────────────

def enviar_mensagem(texto: str, parse_mode: str = None) -> bool:
    """
    Envia uma mensagem de texto para o chat configurado.

    Args:
        texto:      Conteúdo da mensagem.
        parse_mode: "HTML" ou "Markdown" (None = texto puro, recomendado).

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    if not telegram_configurado():
        logger.warning(
            "Telegram não configurado. "
            "Defina TELEGRAM_ATIVO=True, TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no config.py"
        )
        return False

    token  = config.TELEGRAM_TOKEN.strip()
    chatid = config.TELEGRAM_CHAT_ID.strip()
    url    = _API_URL.format(token=token, metodo="sendMessage")

    payload = {
        "chat_id":                  chatid,
        "text":                     texto,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            resp = requests.post(url, json=payload, timeout=15)

            # Rate limit: aguarda o tempo indicado pelo Telegram e tenta de novo
            if resp.status_code == 429:
                try:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 30)
                except Exception:
                    retry_after = 30
                logger.warning(
                    "Telegram: rate limit (429). Aguardando %ds antes de tentar novamente "
                    "(tentativa %d/%d).", retry_after, tentativa, max_tentativas
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram: mensagem enviada (%d chars)", len(texto))
                return True
            else:
                logger.error(
                    "Telegram retornou erro: %s",
                    data.get("description", "resposta desconhecida")
                )
                return False

        except requests.exceptions.ConnectionError:
            logger.error("Telegram: sem conexão com a internet.")
            return False
        except requests.exceptions.Timeout:
            logger.error("Telegram: timeout ao enviar mensagem.")
            return False
        except requests.exceptions.HTTPError as exc:
            logger.error("Telegram: HTTP %s — %s", exc.response.status_code, exc)
            return False
        except Exception as exc:
            logger.error("Telegram: erro inesperado — %s", exc)
            return False

    logger.error("Telegram: máximo de tentativas atingido após rate limit.")
    return False


# ── Envio do boletim (com divisão automática) ─────────────────────────────────

def enviar_boletim(texto: str) -> bool:
    """
    Envia o boletim completo para o Telegram.

    Se o texto ultrapassar TELEGRAM_MAX_CHARS, divide em partes e envia
    cada uma sequencialmente. Falhas parciais são registradas mas não
    interrompem o envio das demais partes.

    Returns:
        True se todas as partes foram enviadas, False se alguma falhou.
    """
    if not telegram_configurado():
        logger.warning(
            "Telegram não configurado — boletim não enviado. "
            "Configure TELEGRAM_ATIVO, TELEGRAM_TOKEN e TELEGRAM_CHAT_ID."
        )
        return False

    dividir = getattr(config, "TELEGRAM_DIVIDIR_MENSAGEM", True)
    prefixo = getattr(config, "TELEGRAM_PREFIXO_PARTES", True)
    limite  = getattr(config, "TELEGRAM_MAX_CHARS", 3900)

    if not dividir:
        # Truncar em vez de dividir
        if len(texto) > limite:
            texto = texto[:limite - 20] + "\n\n[mensagem truncada]"
        return enviar_mensagem(texto)

    partes = dividir_texto(texto, limite)
    total  = len(partes)

    logger.info(
        "Telegram: enviando boletim em %d parte(s) (~%d chars total)",
        total, len(texto)
    )

    sucesso_total = True

    for i, parte in enumerate(partes, start=1):
        # Cabeçalho de parte quando houver mais de uma
        if total > 1 and prefixo:
            cabecalho = f"[Parte {i}/{total}]\n"
            # Garante que o cabeçalho + conteúdo cabem no limite
            if len(cabecalho) + len(parte) > limite:
                parte = parte[:limite - len(cabecalho)]
            parte = cabecalho + parte

        ok = enviar_mensagem(parte)
        if not ok:
            logger.error("Telegram: falha ao enviar parte %d/%d", i, total)
            sucesso_total = False
        else:
            logger.info("Telegram: parte %d/%d enviada.", i, total)

        # Pausa entre partes para respeitar rate limit
        if i < total:
            time.sleep(_PAUSA_ENTRE_PARTES)

    if sucesso_total:
        logger.info("Telegram: boletim enviado com sucesso (%d parte(s)).", total)
    else:
        logger.warning("Telegram: boletim enviado com falhas em algumas partes.")

    return sucesso_total


# ── Diagnóstico ───────────────────────────────────────────────────────────────

def testar_conexao() -> bool:
    """
    Envia mensagem de teste para verificar a conexão.
    Retorna True se bem-sucedido.
    """
    msg = (
        "✅ News Hunter conectado ao Telegram com sucesso.\n"
        "O boletim diário será enviado nos horários configurados."
    )
    ok = enviar_mensagem(msg)
    if ok:
        print("  ✅ Telegram: conexão OK!")
    else:
        print("  ❌ Telegram: falha na conexão. Verifique config.py.")
    return ok
