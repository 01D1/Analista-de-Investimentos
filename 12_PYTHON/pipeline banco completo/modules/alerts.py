"""
alerts.py — Alertas via Telegram para eventos de valuation.

Dispara notificação quando uma das condições é atingida:
  - Recomendação BUY (qualquer variante)
  - Upside > ALERTA_UPSIDE_MIN e Score > ALERTA_SCORE_MIN
  - Score subiu >= ALERTA_DELTA_SCORE em relação ao run anterior

Rate limiting: não re-alerta o mesmo ticker+recomendação em menos de
ALERTA_COOLDOWN_HORAS horas (rastreado em data/alerts_log.json).

Resolução de credenciais (ordem de prioridade):
  1. Variáveis de ambiente / .env do pipeline (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
  2. config.py do news_hunter (fallback automático — sem precisar reconfigurar)

Nunca interrompe o pipeline em caso de falha.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger("pipeline.alerts")

_ROOT = Path(__file__).parent.parent
_LOG_PATH = _ROOT / "data" / "alerts_log.json"
_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# ─────────────────────────────────────────────────────────────────────────────
# Configuração (lida do ambiente em tempo de execução)
# ─────────────────────────────────────────────────────────────────────────────

_NEWS_HUNTER_DIR = Path(__file__).parent.parent.parent / "news_hunter"


def _credenciais_news_hunter() -> tuple[str, str]:
    """
    Tenta ler TELEGRAM_TOKEN e TELEGRAM_CHAT_ID do config.py do news_hunter.
    Retorna ("", "") se não conseguir importar.
    """
    if not _NEWS_HUNTER_DIR.exists():
        return "", ""
    try:
        if str(_NEWS_HUNTER_DIR) not in sys.path:
            sys.path.insert(0, str(_NEWS_HUNTER_DIR))
        import importlib
        nh_cfg = importlib.import_module("config")
        token   = getattr(nh_cfg, "TELEGRAM_TOKEN",   "").strip()
        chat_id = getattr(nh_cfg, "TELEGRAM_CHAT_ID", "").strip()
        return token, chat_id
    except Exception:
        return "", ""


def _cfg() -> dict:
    """
    Lê configurações em runtime.
    Prioridade: env/.env do pipeline → config.py do news_hunter.
    """
    token   = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        nh_token, nh_chat = _credenciais_news_hunter()
        token   = token   or nh_token
        chat_id = chat_id or nh_chat
        if token and chat_id:
            logger.debug("[alerts] Usando credenciais Telegram do news_hunter")

    return {
        "token":       token,
        "chat_id":     chat_id,
        "upside_min":  float(os.getenv("ALERTA_UPSIDE_MIN",    "0.25")),
        "score_min":   int(os.getenv("ALERTA_SCORE_MIN",       "60")),
        "delta_score": int(os.getenv("ALERTA_DELTA_SCORE",     "15")),
        "cooldown_h":  float(os.getenv("ALERTA_COOLDOWN_HORAS","12")),
    }


def _configurado() -> bool:
    c = _cfg()
    return bool(c["token"] and c["chat_id"])


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting via JSON local
# ─────────────────────────────────────────────────────────────────────────────

def _carregar_log() -> dict:
    if _LOG_PATH.exists():
        try:
            return json.loads(_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _salvar_log(log: dict) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _dentro_do_cooldown(ticker: str, recomendacao: str) -> bool:
    """Retorna True se o mesmo alerta foi enviado dentro do período de cooldown."""
    c = _cfg()
    log = _carregar_log()
    chave = f"{ticker}_{recomendacao}"
    ultimo = log.get(chave)
    if not ultimo:
        return False
    try:
        dt_ultimo = datetime.fromisoformat(ultimo)
        return datetime.now() - dt_ultimo < timedelta(hours=c["cooldown_h"])
    except Exception:
        return False


def _registrar_alerta(ticker: str, recomendacao: str) -> None:
    log = _carregar_log()
    chave = f"{ticker}_{recomendacao}"
    log[chave] = datetime.now().isoformat()
    # Limpa entradas antigas (> 7 dias) para não crescer indefinidamente
    cutoff = datetime.now() - timedelta(days=7)
    log = {k: v for k, v in log.items()
           if datetime.fromisoformat(v) > cutoff}
    log[chave] = datetime.now().isoformat()
    _salvar_log(log)


# ─────────────────────────────────────────────────────────────────────────────
# Envio Telegram (texto puro, sem Markdown)
# ─────────────────────────────────────────────────────────────────────────────

def _enviar(texto: str) -> bool:
    """Envia mensagem de texto puro. Retorna True se ok, False se falhou."""
    c = _cfg()
    url = _API_URL.format(token=c["token"])
    payload = {
        "chat_id": c["chat_id"],
        "text": texto,
        "disable_web_page_preview": True,
    }
    for tentativa in range(1, 4):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 429:
                retry = resp.json().get("parameters", {}).get("retry_after", 30)
                logger.warning("[alerts] Rate limit Telegram — aguardando %ds", retry)
                time.sleep(retry)
                continue
            resp.raise_for_status()
            if resp.json().get("ok"):
                return True
            logger.error("[alerts] Telegram retornou erro: %s",
                         resp.json().get("description"))
            return False
        except requests.exceptions.ConnectionError:
            logger.error("[alerts] Telegram: sem conexão")
            return False
        except Exception as exc:
            logger.error("[alerts] Telegram: erro na tentativa %d — %s", tentativa, exc)
            if tentativa < 3:
                time.sleep(2)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Formatação da mensagem
# ─────────────────────────────────────────────────────────────────────────────

def _formatar_alerta(
    analise: dict,
    valuation: dict,
    mercado: dict,
    motivo: str,
) -> str:
    ticker = analise.get("ticker", "?")
    nome   = analise.get("nome", "")
    rec    = analise.get("recomendacao", "?")
    score  = analise.get("score", 0)
    risco  = analise.get("risco", "?")
    conf   = analise.get("confianca", "?")
    tese   = analise.get("tese", "")

    pa  = valuation.get("preco_atual") or mercado.get("preco") or 0
    pj  = valuation.get("preco_justo_on") or 0
    up  = valuation.get("upside_on") or analise.get("detalhes", {}).get("upside_on") or 0
    tir = valuation.get("tir_on") or analise.get("detalhes", {}).get("tir_on") or 0
    pt  = valuation.get("preco_teto_on") or 0

    icone = {
        "BUY": "COMPRA",
        "HOLD": "NEUTRO",
        "SELL": "VENDA",
        "AVOID": "EVITAR",
    }.get(rec.split()[0], rec)

    linhas = [
        f"[VALUATION] {icone} — {ticker}",
        f"Empresa: {nome}",
        "",
        f"Cotacao atual:  R$ {pa:.2f}",
        f"Preco justo:    R$ {pj:.2f}",
        f"Upside:         {up:+.1%}",
        f"TIR:            {tir:.1%}",
    ]
    if pt:
        linhas.append(f"Preco teto:     R$ {pt:.2f}")
    linhas += [
        "",
        f"Score:       {score}/100",
        f"Risco:       {risco}",
        f"Confianca:   {conf}",
        f"Motivo:      {motivo}",
        "",
        f"Tese: {tese}",
        "",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]
    return "\n".join(linhas)


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def verificar_e_alertar(
    analise: dict,
    valuation: dict,
    mercado: dict,
    delta_score: Optional[int] = None,
) -> bool:
    """
    Verifica condições e envia alerta Telegram se necessário.

    Args:
        analise:     Resultado de intelligence.analisar_valuation()
        valuation:   Dict de valuation do pipeline
        mercado:     Dict de dados de mercado
        delta_score: Variação de score em relação ao run anterior (opcional).
                     Passe o valor de database.comparar_runs()["delta_score"].

    Returns:
        True se alerta foi enviado, False caso contrário.
    """
    if not _configurado():
        logger.debug("[alerts] Telegram não configurado — alertas desativados")
        return False

    c = _cfg()
    ticker = analise.get("ticker", "?")
    rec    = analise.get("recomendacao", "")
    score  = analise.get("score", 0)
    upside = analise.get("detalhes", {}).get("upside_on", 0.0) or 0.0

    # ── Verificar condições ────────────────────────────────────────────────
    motivo = None

    if rec.startswith("BUY"):
        motivo = f"Recomendacao BUY (score={score})"

    elif upside >= c["upside_min"] and score >= c["score_min"]:
        motivo = f"Upside {upside:+.1%} com score {score}/100"

    elif delta_score is not None and delta_score >= c["delta_score"]:
        motivo = f"Score subiu {delta_score:+d} pontos neste run"

    if motivo is None:
        return False

    # ── Rate limiting ──────────────────────────────────────────────────────
    if _dentro_do_cooldown(ticker, rec):
        logger.info("[alerts] %s — cooldown ativo, alerta suprimido", ticker)
        return False

    # ── Formatar e enviar ──────────────────────────────────────────────────
    texto = _formatar_alerta(analise, valuation, mercado, motivo)
    ok = _enviar(texto)

    if ok:
        _registrar_alerta(ticker, rec)
        logger.info("[alerts] Alerta enviado para %s — motivo: %s", ticker, motivo)
    else:
        logger.warning("[alerts] Falha ao enviar alerta para %s", ticker)

    return ok


def testar_conexao() -> bool:
    """Envia mensagem de teste para verificar configuração do Telegram."""
    if not _configurado():
        logger.error("[alerts] TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não definidos no .env")
        return False
    ok = _enviar(
        "[Pipeline Valuation] Conexao com Telegram OK.\n"
        "Alertas de BUY/Upside serao enviados aqui."
    )
    if ok:
        logger.info("[alerts] Telegram OK")
    return ok
